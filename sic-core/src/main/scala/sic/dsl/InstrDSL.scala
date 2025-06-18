package sic.dsl
import sic.*, sic.primitives.*

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