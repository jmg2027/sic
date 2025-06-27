package sic.catalogue

import sic._
import sic.dsl.InstrDSL._
import sic.primitives._

/** Placeholder RV32C compressed instructions (subset). */
object RV32C {
  val C_ADDI4SPN = instr("C.ADDI4SPN", CI, opcode = 0x0) { List() }
  val C_LW = instr("C.LW", CI, opcode = 0x0) { List() }
  val C_SW = instr("C.SW", CI, opcode = 0x0) { List() }
  val C_NOP = instr("C.NOP", CI, opcode = 0x1) { List() }
  val C_ADDI = instr("C.ADDI", CI, opcode = 0x1) { List() }
  val C_J = instr("C.J", CB, opcode = 0x5) { List() }
  val C_BEQZ = instr("C.BEQZ", CB, opcode = 0x6) { List() }
  val C_BNEZ = instr("C.BNEZ", CB, opcode = 0x7) { List() }
  val C_SLLI = instr("C.SLLI", CI, opcode = 0x2) { List() }
  val C_LWSP = instr("C.LWSP", CI, opcode = 0x2) { List() }
  val C_SWSP = instr("C.SWSP", CI, opcode = 0x2) { List() }

  val catalogue: Vector[InstrDesc] =
    Vector(
      C_ADDI4SPN,
      C_LW,
      C_SW,
      C_NOP,
      C_ADDI,
      C_J,
      C_BEQZ,
      C_BNEZ,
      C_SLLI,
      C_LWSP,
      C_SWSP
    )
}
