package sic.primitives

sealed trait Prim
final case class READ_REG(id: Int)                 extends Prim
// final case class WRITE_REG(id: Int, v: Expr)       extends Prim
// … 18개 전부 기입