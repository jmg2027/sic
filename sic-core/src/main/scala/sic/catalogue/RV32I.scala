package sic.catalogue

import sic._ // core types (Format, FieldRange…)
import sic.dsl.InstrDSL._ // instr builder
import sic.primitives._ // Expr, PrimInvoke…

/** == RV32I Instruction Catalogue ==
  *
  * _Single source‑of‑truth_ for all 47 base ISA instructions.  – Field
  * bit‑ranges are auto‑inferred from [[Format]].  – Semantics blocks are
  * **stubbed** for brevity; fill them incrementally.
  *
  * Usage:
  * {{{
  *   import sic.catalogue.RV32I.catalogue
  * }}}
  */
object RV32I {

  // ------------------------------------------------------------------
  // Common symbolic references
  // ------------------------------------------------------------------
  private val pc = Ref("pc")
  private val instLen = Lit(4, 32) // TODO: RVC = 2/4

  // ------------------------------------------------------------------
  // U‑type  (LUI, AUIPC)
  // ------------------------------------------------------------------
  /** Load Upper Immediate. */
  val LUI: InstrDesc = instr("LUI", U, opcode = 0x37) {
    List(
      // rd ← imm[31:12] << 12
      PrimInvoke(
        WRITE_REG(
          id = 0, // placeholder; rd extraction TBD
          v = SEXT(Bin("<<", Ref("imm"), Lit(12, 32)), 32)
        )
      ),
      PrimInvoke(ADV_PC(4))
    )
  }

  /** Add Upper Immediate to PC. */
  val AUIPC: InstrDesc = instr("AUIPC", U, opcode = 0x17) {
    List(
      Let("tmp", Bin("+", pc, SEXT(Bin("<<", Ref("imm"), Lit(12, 32)), 32))),
      PrimInvoke(WRITE_REG(id = 0, v = Ref("tmp"))), // rd placeholder
      PrimInvoke(ADV_PC(4))
    )
  }

  // ------------------------------------------------------------------
  // UJ‑type  (JAL)
  // ------------------------------------------------------------------
  val JAL: InstrDesc = instr("JAL", UJ, opcode = 0x6f) {
    List(
      // target = pc + sext(imm) << 1
      Let("tgt", Bin("+", pc, Bin("<<", SEXT(Ref("imm"), 32), Lit(1, 32)))),
      PrimInvoke(WRITE_REG(id = 0, v = Bin("+", pc, instLen))),
      PrimInvoke(SET_PC(Ref("tgt")))
    )
  }

  // ------------------------------------------------------------------
  // I‑type  (JALR, … stub)
  // ------------------------------------------------------------------
  val JALR: InstrDesc = instr("JALR", I, opcode = 0x67) { List() }

  // TODO: ADDI, SLTI, … loads, etc.

  // ------------------------------------------------------------------
  // S‑type (stores)  — stub
  // ------------------------------------------------------------------
  // val SW: InstrDesc = …

  // ------------------------------------------------------------------
  // B‑type (branches) — stub
  // ------------------------------------------------------------------
  // val BEQ: InstrDesc = …

  // ------------------------------------------------------------------
  // R‑type (reg‑reg ALU) — stub
  // ------------------------------------------------------------------
  // val ADD: InstrDesc = …

  // ------------------------------------------------------------------
  // Public aggregated vector
  // ------------------------------------------------------------------
  val catalogue: Vector[InstrDesc] =
    Vector(
      // U
      LUI,
      AUIPC,
      // UJ
      JAL,
      // I
      JALR
      // S, B, R … (추가 예정)
    )
}
