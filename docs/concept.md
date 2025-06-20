## 1  Big‑picture data‑flow

```text
      ┌──────────────┐  build‑time   ┌──────────────┐  elaboration   ┌──────────────┐  run‑time
      │  RV32I.scala │──────────────▶│  Code‑gen    │───────────────▶│ Decode ROM   │──────────▶  pipeline ctrl
      └──────────────┘  (Scala JVM)  │  (Scala/Chisel)│  (Chisel RTL) └──────────────┘
           ▲                           └─ emits:                          ▲
           │                               • masks/values (decoder)       │
           │                               • field extract logic          │
           │                               • **InstProperty** bits        │
           │                               • vector[Prim] descriptor      │
           │                                                              │
           └──────────────  round‑trips to YAML / docs / tests  ◀─────────┘
```

* **Catalogue (`RV32I.scala`)** – declarative, side‑effect free.
* **Code‑gen** – a Scala object that folds over every `InstrDesc`,
  producing three artefacts the hardware actually needs:

  1. **Decode table** `(mask,value) → index`.
  2. **Field extract wiring** based on `FormatFields`.
  3. **InstProperty bundle** – one‑hot or bit‑vector telling the pipeline
     “what kind of instruction is this?”.
  4. **Vector\[Prim]** – retained for back‑end generators
     (scoreboard, commit logic, formal proof).

Everything after code‑gen is auto‑derived; no hand‑maintenance is required
when you add a new instruction or extension.

---

## 2  `InstProperty` — the contract between *semantic* and *micro‑arch*

```scala
/** One‑bit flags consumed by the pipeline. */
final case class InstProperty(
  isALU      : Boolean = false,
  isLoad     : Boolean = false,
  isStore    : Boolean = false,
  isBranch   : Boolean = false,   // conditional
  isJump     : Boolean = false,   // JAL/JALR
  isCSR      : Boolean = false,
  writesRd   : Boolean = false,
  readsRs1   : Boolean = false,
  readsRs2   : Boolean = false,
  mayRaise   : Boolean = false    // any RAISE/ECALL/EBREAK
)
```

### 2.1 Automatic derivation rules (pure functions)

| Semantic evidence in `Prim` list                             | Property bit → `true`             |
| ------------------------------------------------------------ | --------------------------------- |
| at least one `ADD`, `SUB`, `Bin(...)` *without* `LOAD/STORE` | `isALU`                           |
| `LOAD` present                                               | `isLoad`, `readsRs1`              |
| `STORE` present                                              | `isStore`, `readsRs1`, `readsRs2` |
| `SET_PC` **and** conditional test (`Let("take", …)`)         | `isBranch`                        |
| `SET_PC` **without** condition                               | `isJump`                          |
| any `CSR_OP`                                                 | `isCSR`, `writesRd`               |
| any `WRITE_REG(rd,·)` where `rd≠0`                           | `writesRd`                        |
| any `READ_REG(rs1)`                                          | `readsRs1`                        |
| any `READ_REG(rs2)`                                          | `readsRs2`                        |
| `RAISE`, `ECALL`, `EBREAK`                                   | `mayRaise`                        |

> **Implementation**: write a function
> `def deriveProps(stmts: List[Stmt]): InstProperty`
> that pattern‑matches once and returns the `copy()` diff.

---

## 3  Example – code‑gen snippet (`DecodeROM.scala`)

```scala
/** Compile‑time generator; called from sbt‑>Chisel stage. */
object DecodeROM {

  import chisel3._
  import sic.catalogue.SIC

  private case class RomEntry(
    mask      : BigInt,
    value     : BigInt,
    props     : InstProperty,
    primIndex : Int                // index into separate Prim memory
  )

  /** Materialised once at elaboration. */
  val table: Vector[RomEntry] = {
    var primAcc = Vector.empty[Vector[Prim]]    // parallel memory
    SIC.catalogue.zipWithIndex.map { case (d, idx) =>
      primAcc :+= d.semantics.collect { case PrimInvoke(p) => p }
      RomEntry(
        mask      = d.decodeKey.mask,
        value     = d.decodeKey.value,
        props     = deriveProps(d.semantics),
        primIndex = idx
      )
    }.toVector
  }

  /** Chisel literal `Vec` holding masks/values/properties. */
  def romLiteral: Vec[UInt] = {
    VecInit(table.map { e =>
      Cat(
        e.mask.U(32.W),
        e.value.U(32.W),
        e.props.asUInt        // InstProperty extends Record
      )
    })
  }
}
```

* The **front‑end stage** does:

  * parallel compare (word & mask == value) over the ROM rows;
  * first hit gives both an *index* and the **InstProperty** word.
* The index fetches the pre‑decoded `Prim` vector if a subsequent stage
  (commit, reorder buffer, formal monitor) wants to replay semantic actions.

---

## 4  Where **Expr** participates

*Decoder* never needs `Expr` trees – only *field slices* (`rd`, `rs1`, …).
Those are produced by the **field extract logic** generated from
`FormatFields.table`.

Later stages (e.g. a single‑cycle core or ISS back‑end) may **evaluate**
the `Expr` when executing the corresponding `Prim`.
A superscalar/OOO core may ignore them and substitute its own ALU datapath;
only the *property bits* and *register indices* are required at dispatch time.

---

## 5  Putting it together — walk‑through (JAL example)

| Stage                     | Action                                                                | Data produced               |      |   |
| ------------------------- | --------------------------------------------------------------------- | --------------------------- | ---- | - |
| **Fetch**                 | 32‑bit word = `0x005000EF`                                            | —                           |      |   |
| **Decode‑ROM match**      | `(word & mask)==value` hits row `JAL`                                 | `props.isJump = 1`          |      |   |
| **Field extract**         | `rd = x1`, \`imm\[20                                                  | 10:1                        | …]\` | — |
| **Dispatch**              | sees `isJump`, allocates branch‑unit slot, marks `writesRd`           | —                           |      |   |
| **Execute (branch unit)** | evaluates `target = pc + Sext(imm)<<1` (using Expr AST or native ALU) | computes new PC             |      |   |
| **Commit**                | replays Prim list:<br/>`WRITE_REG`, `SET_PC`                          | architectural state updated |      |   |

No handwritten decoder lines were necessary;
adding `Zcmp` or `B‑extension` ops only requires one more `InstrDesc`
and the generator re‑runs.

---

## 6  Impact on future extensions

* **Vector ‘V’** – more properties (`isVector`, `vectorWidth`, …) derivable
  from the presence of new `Prim`s (`VLOAD`, `VSTORE`) or by adding
  an override map in `InstrDesc`.
* **Hypervisor ‘H’ / Privilege** – flag bits `needsPriv≥S`,
  `isFenceI`, `isWFI` likewise inferred from `Prim` (`CSR_OP`, `FENCE_OP`)
  plus an optional field in `InstrDesc`.
* **Custom accelerators** – just add a new `Prim` (`SHA_ROUND`)
  and teach `deriveProps` the mapping `SHA_ROUND → isSha`.

---

### TL;DR answer to “decoder랑 instproperty랑은?”

* `InstrDesc` (catalogue) → **compile‑time generator** →
  *mask/value*, *field extract*, **InstProperty** bundle, *Prim vector*.
* The **decoder ROM** is literally the materialisation of that table.
* `InstProperty` is a lossless, one‑cycle‑visible summary of the
  semantic layer; the pipeline never guesses.
* Expr/Prim separation is orthogonal: Expr never enters decoder,
  Prim vector is stored for later architectural replay or proofs.