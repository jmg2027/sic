package sic.dsl
import sic._
import sic.primitives._

object InstrDSL {
  def instr(
      name: String,
      format: Format,
      opcode: Int
  )(body: (RegId, Imm) => List[Stmt]): InstrDesc = {
    val semantics = body(0, 0)
    InstrDesc(
      name = name,
      format = format,
      decodeKey = BitPattern.from(opcode, 7),
      fields = Map.empty,
      semantics = semantics
    )
  }
}
