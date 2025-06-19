package sic
import sic.primitives._

final case class InstrDesc(
    name: String,
    format: Format,
    decodeKey: BitPattern,
    fields: Map[String, (Int, Int)],
    semantics: List[Stmt],
    notes: Option[String] = None
)
