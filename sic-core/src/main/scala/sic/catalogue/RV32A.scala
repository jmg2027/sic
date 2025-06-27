package sic.catalogue

import sic._
import sic.dsl.InstrDSL._
import sic.primitives._

/** Placeholder RV32A atomic instructions. */
object RV32A {
  val LR_W = instr("LR.W", R, opcode = 0x2f) { List() }
  val SC_W = instr("SC.W", R, opcode = 0x2f) { List() }
  val AMOSWAP_W = instr("AMOSWAP.W", R, opcode = 0x2f) { List() }
  val AMOADD_W = instr("AMOADD.W", R, opcode = 0x2f) { List() }
  val AMOXOR_W = instr("AMOXOR.W", R, opcode = 0x2f) { List() }
  val AMOAND_W = instr("AMOAND.W", R, opcode = 0x2f) { List() }
  val AMOOR_W = instr("AMOOR.W", R, opcode = 0x2f) { List() }
  val AMOMIN_W = instr("AMOMIN.W", R, opcode = 0x2f) { List() }
  val AMOMAX_W = instr("AMOMAX.W", R, opcode = 0x2f) { List() }
  val AMOMINU_W = instr("AMOMINU.W", R, opcode = 0x2f) { List() }
  val AMOMAXU_W = instr("AMOMAXU.W", R, opcode = 0x2f) { List() }

  val catalogue: Vector[InstrDesc] =
    Vector(
      LR_W,
      SC_W,
      AMOSWAP_W,
      AMOADD_W,
      AMOXOR_W,
      AMOAND_W,
      AMOOR_W,
      AMOMIN_W,
      AMOMAX_W,
      AMOMINU_W,
      AMOMAXU_W
    )
}
