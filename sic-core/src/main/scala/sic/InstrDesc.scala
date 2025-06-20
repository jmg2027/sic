package sic
import sic.primitives._

/** Immutable, fully‑typed description of a single instruction.
  *
  * ==Fields==
  * @param name
  *   Human‑readable mnemonic (e.g. `"JAL"`).
  * @param format
  *   Instruction encoding `Format`; aids immediate extraction.
  * @param decodeKey
  *   `(mask,value)` pair covering *at least* opcode; may include funct3/funct7
  *   for uniqueness.
  * @param fields
  *   Mapping from semantic names (`"rd"`, `"imm"`) to their bit‑ranges within
  *   the 32‑bit word (msb ≥ lsb).
  * @param semantics
  *   Ordered list of `Stmt` representing architecturally visible behaviour.
  * @param notes
  *   Optional free‑text for spec cross‑refs.
  *
  * ==Example==
  * {{{
  * InstrDesc(
  *   "LUI", U,
  *   decodeKey = BitPattern.fromWidth(0x37,7),
  *   fields    = Map("rd" -> FieldRange(11,7), "imm" -> FieldRange(31,12)),
  *   semantics = List( … )
  * )
  * }}}
  */
final case class FieldRange(msb: Int, lsb: Int) {
  require(msb >= lsb, "msb must be ≥ lsb")
  val width: Int = msb - lsb + 1
}

final case class InstrDesc(
    name: String,
    format: Format,
    decodeKey: BitPattern,
    fields: Map[String, FieldRange],
    semantics: List[Stmt],
    notes: Option[String] = None
)

// src/main/scala/sic/InstrDesc.scala
object InstrDesc {

  /** Smart‑constructor: 자동 필드 주입 + 사용자 커스텀 병합.
    *
    * @param custom
    *   format 기본 필드를 덮어쓰거나 추가할 Map
    */
  def build( // ← 이름을 'build' 로 변경
      name: String,
      format: Format,
      decodeKey: BitPattern,
      semantics: List[Stmt],
      custom: Map[String, FieldRange] = Map.empty,
      notes: Option[String] = None
  ): InstrDesc = {
    val auto = FormatFields.table.getOrElse(format, Map.empty)
    new InstrDesc(name, format, decodeKey, auto ++ custom, semantics, notes)
  }
}
