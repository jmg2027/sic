package sic.primitives

sealed trait Expr
final case class Lit(value: BigInt) extends Expr
final case class Ref(id: Int) extends Expr
final case class Bin(op: String, a: Expr, b: Expr) extends Expr
final case class Un(op: String, x: Expr) extends Expr
