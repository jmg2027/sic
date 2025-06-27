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
  // I‑type (loads, JALR, immediates)
  // ------------------------------------------------------------------
  val JALR: InstrDesc = instr("JALR", I, opcode = 0x67) { List() }
  val LB: InstrDesc = instr("LB", I, opcode = 0x03) { List() }
  val LH: InstrDesc = instr("LH", I, opcode = 0x03) { List() }
  val LW: InstrDesc = instr("LW", I, opcode = 0x03) { List() }
  val LBU: InstrDesc = instr("LBU", I, opcode = 0x03) { List() }
  val LHU: InstrDesc = instr("LHU", I, opcode = 0x03) { List() }
  val ADDI: InstrDesc = instr("ADDI", I, opcode = 0x13) { List() }
  val SLTI: InstrDesc = instr("SLTI", I, opcode = 0x13) { List() }
  val SLTIU: InstrDesc = instr("SLTIU", I, opcode = 0x13) { List() }
  val XORI: InstrDesc = instr("XORI", I, opcode = 0x13) { List() }
  val ORI: InstrDesc = instr("ORI", I, opcode = 0x13) { List() }
  val ANDI: InstrDesc = instr("ANDI", I, opcode = 0x13) { List() }
  val SLLI: InstrDesc = instr("SLLI", I, opcode = 0x13) { List() }
  val SRLI: InstrDesc = instr("SRLI", I, opcode = 0x13) { List() }
  val SRAI: InstrDesc = instr("SRAI", I, opcode = 0x13) { List() }
  val FENCE: InstrDesc = instr("FENCE", I, opcode = 0x0f) { List() }
  val FENCE_I: InstrDesc = instr("FENCE.I", I, opcode = 0x0f) { List() }

  // ------------------------------------------------------------------
  // S‑type (stores)
  // ------------------------------------------------------------------
  val SB: InstrDesc = instr("SB", S, opcode = 0x23) { List() }
  val SH: InstrDesc = instr("SH", S, opcode = 0x23) { List() }
  val SW: InstrDesc = instr("SW", S, opcode = 0x23) { List() }

  // ------------------------------------------------------------------
  // B‑type (branches)
  // ------------------------------------------------------------------
  val BEQ: InstrDesc = instr("BEQ", B, opcode = 0x63) { List() }
  val BNE: InstrDesc = instr("BNE", B, opcode = 0x63) { List() }
  val BLT: InstrDesc = instr("BLT", B, opcode = 0x63) { List() }
  val BGE: InstrDesc = instr("BGE", B, opcode = 0x63) { List() }
  val BLTU: InstrDesc = instr("BLTU", B, opcode = 0x63) { List() }
  val BGEU: InstrDesc = instr("BGEU", B, opcode = 0x63) { List() }

  // ------------------------------------------------------------------
  // R‑type (reg‑reg ALU)
  // ------------------------------------------------------------------
  val ADD: InstrDesc = instr("ADD", R, opcode = 0x33) { List() }
  val SUB: InstrDesc = instr("SUB", R, opcode = 0x33) { List() }
  val SLL: InstrDesc = instr("SLL", R, opcode = 0x33) { List() }
  val SLT: InstrDesc = instr("SLT", R, opcode = 0x33) { List() }
  val SLTU: InstrDesc = instr("SLTU", R, opcode = 0x33) { List() }
  val XOR: InstrDesc = instr("XOR", R, opcode = 0x33) { List() }
  val SRL: InstrDesc = instr("SRL", R, opcode = 0x33) { List() }
  val SRA: InstrDesc = instr("SRA", R, opcode = 0x33) { List() }
  val OR: InstrDesc = instr("OR", R, opcode = 0x33) { List() }
  val AND: InstrDesc = instr("AND", R, opcode = 0x33) { List() }

  // ------------------------------------------------------------------
  // CSR‑type (system)
  // ------------------------------------------------------------------
  val ECALL: InstrDesc = instr("ECALL", CSR, opcode = 0x73) { List() }
  val EBREAK: InstrDesc = instr("EBREAK", CSR, opcode = 0x73) { List() }
  val CSRRW: InstrDesc = instr("CSRRW", CSR, opcode = 0x73) { List() }
  val CSRRS: InstrDesc = instr("CSRRS", CSR, opcode = 0x73) { List() }
  val CSRRC: InstrDesc = instr("CSRRC", CSR, opcode = 0x73) { List() }
  val CSRRWI: InstrDesc = instr("CSRRWI", CSR, opcode = 0x73) { List() }
  val CSRRSI: InstrDesc = instr("CSRRSI", CSR, opcode = 0x73) { List() }
  val CSRRCI: InstrDesc = instr("CSRRCI", CSR, opcode = 0x73) { List() }

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
      // I loads & immediates
      JALR,
      LB,
      LH,
      LW,
      LBU,
      LHU,
      ADDI,
      SLTI,
      SLTIU,
      XORI,
      ORI,
      ANDI,
      SLLI,
      SRLI,
      SRAI,
      FENCE,
      FENCE_I,
      // S
      SB,
      SH,
      SW,
      // B
      BEQ,
      BNE,
      BLT,
      BGE,
      BLTU,
      BGEU,
      // R
      ADD,
      SUB,
      SLL,
      SLT,
      SLTU,
      XOR,
      SRL,
      SRA,
      OR,
      AND,
      // CSR/system
      ECALL,
      EBREAK,
      CSRRW,
      CSRRS,
      CSRRC,
      CSRRWI,
      CSRRSI,
      CSRRCI
    )
}
