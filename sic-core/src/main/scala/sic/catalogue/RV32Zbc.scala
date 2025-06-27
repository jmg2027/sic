package sic.catalogue

import sic._
import sic.dsl.InstrDSL._
import sic.primitives._

/** Placeholder Zbc extension instructions. */
object RV32Zbc {
  val CLMUL = instr("CLMUL", R, opcode = 0x33) { List() }
  val CLMULH = instr("CLMULH", R, opcode = 0x33) { List() }
  val CLMULR = instr("CLMULR", R, opcode = 0x33) { List() }

  val catalogue: Vector[InstrDesc] =
    Vector(CLMUL, CLMULH, CLMULR)
}
