package sic.catalogue

import sic._
import sic.dsl.InstrDSL._
import sic.primitives._

/** Placeholder Zbb extension instructions. */
object RV32Zbb {
  val ANDN = instr("ANDN", R, opcode = 0x33) { List() }
  val ORN = instr("ORN", R, opcode = 0x33) { List() }
  val XNOR = instr("XNOR", R, opcode = 0x33) { List() }
  val CLZ = instr("CLZ", R, opcode = 0x33) { List() }
  val CTZ = instr("CTZ", R, opcode = 0x33) { List() }
  val CPOP = instr("CPOP", R, opcode = 0x33) { List() }
  val MAX = instr("MAX", R, opcode = 0x33) { List() }
  val MAXU = instr("MAXU", R, opcode = 0x33) { List() }
  val MIN = instr("MIN", R, opcode = 0x33) { List() }
  val MINU = instr("MINU", R, opcode = 0x33) { List() }
  val SEXT_B = instr("SEXT.B", R, opcode = 0x33) { List() }
  val SEXT_H = instr("SEXT.H", R, opcode = 0x33) { List() }
  val ZEXT_H = instr("ZEXT.H", R, opcode = 0x33) { List() }
  val ORC_B = instr("ORC.B", R, opcode = 0x33) { List() }
  val REV8 = instr("REV8", R, opcode = 0x33) { List() }
  val ROL = instr("ROL", R, opcode = 0x33) { List() }
  val ROR = instr("ROR", R, opcode = 0x33) { List() }
  val RORI = instr("RORI", I, opcode = 0x13) { List() }

  val catalogue: Vector[InstrDesc] =
    Vector(
      ANDN,
      ORN,
      XNOR,
      CLZ,
      CTZ,
      CPOP,
      MAX,
      MAXU,
      MIN,
      MINU,
      SEXT_B,
      SEXT_H,
      ZEXT_H,
      ORC_B,
      REV8,
      ROL,
      ROR,
      RORI
    )
}
