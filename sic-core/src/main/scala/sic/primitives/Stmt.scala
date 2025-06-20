package sic.primitives

/** Single‑assignment statement tree.
  *
  * A `Stmt` sequence represents the <u>complete, ordered</u> semantics of a
  * RISC‑V instruction after decoding.
  *
  * ==Categories==
  *   1. `PrimInvoke` — atomic primitive action (side‑effect may raise traps).
  *      2. `Let`        — pure binding to avoid recomputation (SSA‑style). 3.
  *      `SeqBlock`   — ordered list of sub‑statements.
  *
  * ==Ordering Rule==
  * Evaluation is strictly top‑to‑bottom; later `PrimInvoke`s see all previous
  * state updates (architectural, not micro‑arch).
  */
sealed trait Stmt

/** Invoke a single primitive action. */
final case class PrimInvoke(p: Prim) extends Stmt

/** Introduce an immutable temporary visible to subsequent statements. */
final case class Let(name: String, e: Expr) extends Stmt

/** Ordered block; analogous to `{ … }` in C. */
final case class SeqBlock(body: List[Stmt]) extends Stmt
