package sic.catalogue

import sic._
import sic.dsl.InstrDSL._
import sic.primitives._

/** Placeholder Zba extension instructions. */
object RV32Zba {
  val SH1ADD = instr("SH1ADD", R, opcode = 0x33) { List() }
  val SH2ADD = instr("SH2ADD", R, opcode = 0x33) { List() }
  val SH3ADD = instr("SH3ADD", R, opcode = 0x33) { List() }
  val ADD_UW = instr("ADD.UW", R, opcode = 0x33) { List() }
  val SH1ADD_UW = instr("SH1ADD.UW", R, opcode = 0x33) { List() }
  val SH2ADD_UW = instr("SH2ADD.UW", R, opcode = 0x33) { List() }
  val SH3ADD_UW = instr("SH3ADD.UW", R, opcode = 0x33) { List() }
  val SLLI_UW = instr("SLLI.UW", R, opcode = 0x33) { List() }
  val ZEXT_W = instr("ZEXT.W", R, opcode = 0x33) { List() }

  val catalogue: Vector[InstrDesc] =
    Vector(
      SH1ADD,
      SH2ADD,
      SH3ADD,
      ADD_UW,
      SH1ADD_UW,
      SH2ADD_UW,
      SH3ADD_UW,
      SLLI_UW,
      ZEXT_W
    )
}
