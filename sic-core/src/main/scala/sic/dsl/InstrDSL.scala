package sic.dsl
import sic._
import sic.primitives._

/** Lightweight embedded DSL for writing `InstrDesc` values.
  *
  * Target audience: ISA‑spec engineers who prefer code over YAML but still want
  * near‑spec readability. Macros may later upgrade this DSL to accept
  * quasi‑quotes (`pc + sext(imm,20)`).
  *
  * ==Usage==
  * {{{
  * val LUI = instr("LUI", U, opcode = 0x37,
  *                 fields = Map("imm20" -> FieldRange(31,12), "rd" -> FieldRange(11,7))) {
  *   List(
  *     PrimInvoke(WRITE_REG(rd, SEXT(imm20 << 12, 32))),
  *     PrimInvoke(ADV_PC(4))
  *   )
  * }
  * }}}
  *
  * @param name
  *   mnemonic
  * @param format
  *   encoding format
  * @param opcode
  *   7‑bit base opcode (lower bits of `decodeKey`)
  * @param fields
  *   map of named bit‑ranges (optional; can be empty)
  * @param sem
  *   by‑name parameter returning full semantic statement list
  */
object InstrDSL {

  // ------------------------------------------------------------------
  // Private helpers
  // ------------------------------------------------------------------

  /** Build a `(mask,value)` for an exact 7‑bit opcode match. */
  private def opcodePattern(op: Int): BitPattern =
    BitPattern(mask = BigInt(0x7f), value = BigInt(op))

  // ------------------------------------------------------------------
  // Public builder
  // ------------------------------------------------------------------

  def instr(
      name: String,
      format: Format,
      opcode: Int,
      fields: Map[String, FieldRange] = Map.empty
  )(sem: => List[Stmt]): InstrDesc =
    InstrDesc.build(
      name = name,
      format = format,
      decodeKey = opcodePattern(opcode),
      semantics = sem
    )
}
