package sic.dsl
import sic._
import sic.primitives._

object InstrDSL {
  def instr(
      name: String,
      format: Format,
      opcode: Int
  )(body: (RegId, Imm) => List[Stmt]): InstrDesc = {
    // 추후 BitPattern 계산 로직 삽입
    ???
  }
}
