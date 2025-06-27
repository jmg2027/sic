package sic.catalogue

import sic._
import sic.dsl.InstrDSL._
import sic.primitives._

/** Placeholder Zbs extension instructions. */
object RV32Zbs {
  val BCLR = instr("BCLR", R, opcode = 0x33) { List() }
  val BCLRI = instr("BCLRI", I, opcode = 0x13) { List() }
  val BEXT = instr("BEXT", R, opcode = 0x33) { List() }
  val BEXTI = instr("BEXTI", I, opcode = 0x13) { List() }
  val BINV = instr("BINV", R, opcode = 0x33) { List() }
  val BINVI = instr("BINVI", I, opcode = 0x13) { List() }
  val BSET = instr("BSET", R, opcode = 0x33) { List() }
  val BSETI = instr("BSETI", I, opcode = 0x13) { List() }

  val catalogue: Vector[InstrDesc] =
    Vector(BCLR, BCLRI, BEXT, BEXTI, BINV, BINVI, BSET, BSETI)
}
