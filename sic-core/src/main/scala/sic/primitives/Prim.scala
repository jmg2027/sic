package sic.primitives

sealed trait Prim
final case class READ_REG(id: Int) extends Prim
final case class WRITE_REG(id: Int, v: Expr) extends Prim
final case class READ_CSR(id: Int) extends Prim
final case class WRITE_CSR(id: Int, v: Expr) extends Prim
final case class SET_PC(v: Expr) extends Prim
final case class GET_PC() extends Prim
final case class RAISE(msg: String) extends Prim
// ... additional primitives can be added here
