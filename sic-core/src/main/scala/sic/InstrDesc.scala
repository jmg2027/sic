package sic
import sic.primitives.*

final case class BitPattern(mask: BigInt, value: BigInt)

final case class InstrDesc(
  name:      String,
  format:    Format,
  decodeKey: BitPattern,
  fields:    Map[String, (Int, Int)],
  semantics: List[Stmt],
  notes:     Option[String] = None
)
