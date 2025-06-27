package sic.catalogue

import sic._
import sic.dsl.InstrDSL._
import sic.primitives._

/** Placeholder RV32M multiplication/division instructions. */
object RV32M {
  val MUL = instr("MUL", R, opcode = 0x33) { List() }
  val MULH = instr("MULH", R, opcode = 0x33) { List() }
  val MULHSU = instr("MULHSU", R, opcode = 0x33) { List() }
  val MULHU = instr("MULHU", R, opcode = 0x33) { List() }
  val DIV = instr("DIV", R, opcode = 0x33) { List() }
  val DIVU = instr("DIVU", R, opcode = 0x33) { List() }
  val REM = instr("REM", R, opcode = 0x33) { List() }
  val REMU = instr("REMU", R, opcode = 0x33) { List() }

  val catalogue: Vector[InstrDesc] =
    Vector(MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU)
}
