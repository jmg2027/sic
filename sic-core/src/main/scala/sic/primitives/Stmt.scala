package sic.primitives

sealed trait Stmt
final case class PrimInvoke(p: Prim) extends Stmt
final case class Let(symbol: String, expr: Expr) extends Stmt
final case class SeqStmt(stmts: List[Stmt]) extends Stmt
