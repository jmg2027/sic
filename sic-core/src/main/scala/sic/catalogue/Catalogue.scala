package sic.catalogue
import sic._
import sic.dsl.InstrDSL._
import sic.primitives._

/** ==SIC.catalogue==
  * Single source‑of‑truth instructions from riscv sail
  *
  * Each entry should:
  *   1. Use the `instr` builder. 2. Provide *complete* field maps (for
  *      doc‑gen). 3. Contain **pure** semantic lists (only `PrimInvoke`, `Let`,
  *      `SeqBlock`).
  *
  *  Field bit‑ranges are auto‑inferred from [[Format]].
  */

object SIC {

  /** Full instruction list visible to generators. */
  val catalogue: Vector[sic.InstrDesc] =
    RV32I.catalogue ++
      RV32M.catalogue ++
      RV32A.catalogue ++
      RV32C.catalogue ++
      RV32Zba.catalogue ++
      RV32Zbb.catalogue ++
      RV32Zbc.catalogue ++
      RV32Zbs.catalogue
}
