package sic.primitives

/** Pure, side‑effect‑free expression tree used by `Prim` arguments and
  * let‑bindings.
  *
  * ==Design Rationale==
  *   - Must be _total_ and _referentially transparent_; evaluation cannot raise
  *     traps.
  *   - Keeps the primitive layer ISA‑agnostic: widths are explicit, not
  *     inferred.
  *
  * ==Invariants==
  *   1. All bit‑widths are positive (`width > 0`). 2. No `Expr` node contains
  *      mutable state.
  *
  * ==Example==
  * {{{
  * val addExpr = Bin("+",
  *                  Ref("rs1"),        // source register value
  *                  Lit(BigInt(4),32) // immediate
  *                )
  * }}}
  */
sealed trait Expr

/** Literal constant with a fixed bit‑width. */
final case class Lit(value: BigInt, width: Int) extends Expr {
  require(width > 0, "Bit-width must be positive")
}

/** Named reference (e.g. `pc`, register file read port, temporaries). */
final case class Ref(name: String) extends Expr

/** Binary operator node; `op` follows Verilog naming (`+`,`-`,`<<`). */
final case class Bin(op: String, a: Expr, b: Expr) extends Expr

/** Unary operator node (e.g. `~`,`-`). */
final case class Un(op: String, x: Expr) extends Expr

// ───────────────────────── Sign/Zero extension ───────────────────────
final case class SEXT(v: Expr, w: Int) extends Expr
final case class ZEXT(v: Expr, w: Int) extends Expr
