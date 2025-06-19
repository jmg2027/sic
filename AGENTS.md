# Semantic Instruction Catalogue (SIC) — Development Roadmap
_Last updated: 2025‑06‑18_

## 0 — Repository hygiene
| ✔? | Task | Details |
|----|------|---------|
| ☐ | **.gitignore** | Scala template already added by GitHub; verify `generated/` and IDE folders ignored. |
| ☐ | **LICENSE** | Apache‑2.0 committed at root. |
| ☐ | **README** | Describe project goal, module layout, quick‑start. |
| ☐ | **CONTRIBUTING** | Coding‑style rules, PR checklist, branch policy. |

---

## 1 — sbt & tooling

### 1.1 Plugin wiring
| ✔? | File | Line(s) |
|----|------|---------|
| ☐ | `project/plugins.sbt` | ```scala
addSbtPlugin("org.scalameta" % "sbt-scalafmt" % "2.5.2")
addSbtPlugin("ch.epfl.scala" % "sbt-scalafix" % "0.11.1")
``` |
| ☐ | **Reload** | After editing plugins:  
```bash
sbt reload
``` |

### 1.2 Scalafmt config generation
*Reason for earlier error*: plugin wasn’t loaded yet.  
```bash
# one‑shot outside sbt (after reload)
sbt scalafmtGenerateConfig
# OR inside sbt shell
sbt> scalafmtGenerateConfig

Conf file appears as .scalafmt.conf.
```

### 1.3 Adopt common aliases
Add to ~/.sbt/1.0/global.sbt or project‑level:

```scala
addCommandAlias("fmt",  "scalafmtAll; scalafmtSbt")
addCommandAlias("check","scalafmtCheckAll; Test/compile")
```

---

## 2 — Core data‑types (sic-core)

| ✔? | File | Items to implement / fix |
|-----|------|--------------------------|
| ☐ | sic/primitives/Expr.scala | Minimal AST: Lit, Ref, Bin(op,a,b), Un(op,x). |
| ☐ | sic/primitives/Stmt.scala | PrimInvoke(Prim), Let(symbol, Expr), Seq(List[Stmt]). |
| ☐ | sic/primitives/Prim.scala | 18 primitives (READ_REG … RAISE). |
| ☐ | sic/Format.scala | sealed trait Format + case objects U,I,UJ,S,B,R,CSR,CR,CI,CB. |
| ☐ | sic/BitPattern.scala | mask: BigInt, value: BigInt, helper from(opcode: Int, nBits: Int). |
| ☐ | Compile fix | Replace invalid wildcard import `sic.*` → `sic._`. Same for `sic.primitives._`. |
| ☐ | WRITE_REG compile error | After Expr is defined, `WRITE_REG(id: Int, v: Expr)` compiles. |

---

## 3 — Embedded DSL (sic.dsl)

| ✔? | File / Task | Notes |
|-----|-------------|-------|
| ☐ | InstrDSL.scala | Start with non‑macro builder: accepts lambdas and returns InstrDesc. |
| ☐ | Macro TODO | Once baseline works, migrate to inline/scala‑meta macro to capture quasi‑quotes. |

---

## 4 — Catalogue (sic.catalogue)

| ✔? | Task | Action |
|-----|------|--------|
| ☐ | Catalogue.scala | object SIC { val catalogue: Vector[InstrDesc] = Vector( LUI, AUIPC, JAL, … ) } |
| ☐ | All RV32I entries | Transcribe semantics already drafted in chat; ensure field‑bit maps correct. |
| ☐ | Unit test | `CatalogueCardinalitySpec` asserts `catalogue.size == 47`. |

---

## 5 — Generators (sic-gen)

| ✔? | Task | Command |
|-----|------|---------|
| ☐ | YAML Export | `YamlExport.scala` → `generated/sic.yaml`. |
| ☐ | DecodeROM.scala (stub) | Place in new `sic-rtl/` module; `def apply(desc: InstrDesc): (UInt, UInt)` produces mask/value & index. |
| ☐ | Chisel dep | Add to `sic-rtl` build settings:  
```scala
libraryDependencies += "edu.berkeley.cs" %% "chisel3" % "3.6.0"
``` |

---

## 6 — Testing & CI

| ✔? | Task | Notes |
|-----|------|-------|
| ☐ | ScalaTest | Add `scalatest` % Test; write at least catalogue spec. |
| ☐ | Sail trace diff | Stub in `sic-test/TraceDiff.scala`; integrate later. |
| ☐ | GitHub Actions | `.github/workflows/ci.yml` runs `sbt fmt check`. |

---

## 7 — Documentation

| ✔? | Doc | Content |
|-----|-----|---------|
| ☐ | docs/ARCH.md | Layer diagram, primitive set definition, invariants. |
| ☐ | docs/DSL_GUIDE.md | How to add an instruction with builder syntax. |
| ☐ | docs/ROADMAP.md | Future: RV64, privilege, macros, proof layer. |

---

## 8 — Known compile‑time pitfalls & fixes

1. **`Expr not found`:** ensure `sic.primitives.Expr` exists and is imported.  
2. **Invalid wildcard import:** Scala uses `package._`, not `package.*`.  
3. **`scalafmtGenerateConfig` unknown:** run `reload` after adding plugin; command lives in sbt‑scalafmt ≥ 2.0.  
4. **`DecodeROM` blank:** placeholder in `sic-rtl` until code‑gen phase.  

---

## 9 — Step‑by‑step bootstrap script (Unix)

```bash
### clone & create skeleton #########################################
git clone git@github.com:<ID>/sic.git && cd sic

### tooling
echo 'addSbtPlugin("org.scalameta" % "sbt-scalafmt" % "2.5.2")' >> project/plugins.sbt
echo 'addSbtPlugin("ch.epfl.scala" % "sbt-scalafix" % "0.11.1")' >> project/plugins.sbt
sbt reload scalafmtGenerateConfig

### code scaffold (simplified)
mkdir -p sic-core/src/main/scala/{sic,sic/primitives,sic/dsl,sic/catalogue}
mkdir -p sic-core/src/test/scala/sic
touch sic-core/src/main/scala/sic/primitives/{Expr.scala,Stmt.scala,Prim.scala}
touch sic-core/src/main/scala/sic/{Format.scala,BitPattern.scala}
touch sic-core/src/main/scala/sic/catalogue/Catalogue.scala

### first compile pass
sbt compile

### YAML export demo
mkdir -p generated
sbt "sicGen/runMain sicgen.YamlExport" > generated/sic.yaml
git add .
git commit -m "feat: bootstrap SIC skeleton"
git push
```

---

## 10 — Milestone targets

| ID | Description | Success Criteria |
|----|-------------|------------------|
| M0 | Compiles | `sbt compile` green, catalogue stub present |
| M1 | Complete RV32I | All 47 entries → YAML, unit test passes |
| M2 | Decode ROM | Chisel generator emits synthesizable table |
| M3 | Trace diff | Sail vs. SIC primitive traces identical on isa-tests |
| M4 | v0.1.0 tag | CI green + README guide + public release |

---

Tip: keep each milestone as a GitHub milestone with linked issues; close by PR to ensure review & CI.

---

### How to use

1. Copy the fenced block **verbatim** into `TODO.md`.
2. Check boxes in pull‑requests as tasks complete.
3. Feel free to split long sections into separate docs (`docs/ARCH.md`, etc.) once living documents emerge.