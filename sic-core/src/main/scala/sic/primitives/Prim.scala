package sic.primitives
import sic.primitives.Expr

/** Closed algebra of **primitive architectural actions**.
  *
  * The set is _complete_ for RV32I: every instruction’s observable behaviour
  * can be expressed as an ordered list of these atoms. They are intentionally
  * free of latency / micro‑architecture.
  *
  * ==Conventions==
  *   - All register IDs and CSR IDs are **decoded numerically** (x0≈0,
  *     mstatus≈0x300 …).
  *   - Memory sizes are in **bytes** (1,2,4).
  *   - Booleans follow JVM semantics (`true`=1) unless otherwise noted.
  *
  * ==Exception Semantics==
  * Actions noted “may trap” can throw synchronous exceptions which abort the
  * remainder of the current `Stmt` list. Traps are represented by a `RAISE`
  * tail‑primitive.
  */
sealed trait Prim

// ───────────────────────── Register file ──────────────────────────────
final case class READ_REG(id: Int) extends Prim
final case class WRITE_REG(id: Int, v: Expr) extends Prim

// ───────────────────────── Sign/Zero extension ───────────────────────
// final case class SEXT(v: Expr, w: Int)                   extends Prim
// final case class ZEXT(v: Expr, w: Int)                   extends Prim

// ───────────────────────── Integer ALU (combinational) ───────────────
final case class ADD(a: Expr, b: Expr) extends Prim
final case class SUB(a: Expr, b: Expr) extends Prim
final case class SHL(a: Expr, sh: Expr) extends Prim
final case class SRL(a: Expr, sh: Expr) extends Prim
final case class SRA(a: Expr, sh: Expr) extends Prim
final case class AND(a: Expr, b: Expr) extends Prim
final case class OR(a: Expr, b: Expr) extends Prim
final case class XOR(a: Expr, b: Expr) extends Prim
final case class SLT(a: Expr, b: Expr) extends Prim
final case class SLTU(a: Expr, b: Expr) extends Prim

// ───────────────────────── Program‑counter control ────────────────────
/** PC := PC + len  (no exception). */
final case class ADV_PC(len: Int) extends Prim

/** PC := target    (alignment & PMP faults handled externally). */
final case class SET_PC(t: Expr) extends Prim

// ───────────────────────── Memory system (may trap) ───────────────────
final case class LOAD(addr: Expr, size: Int, sign: Boolean) extends Prim
final case class STORE(addr: Expr, size: Int, data: Expr) extends Prim

// ───────────────────────── Memory‑ordering & system ───────────────────
final case class FENCE_OP(pred: Int, succ: Int) extends Prim

// ───────────────────────── CSR subsystem (may trap) ───────────────────
final case class CSR_OP(id: Int, f: Int, src: Expr) extends Prim

// ───────────────────────── System traps ───────────────────────────────
final case class ECALL() extends Prim
final case class EBREAK() extends Prim

/** Non‑returning exception. `exc` encodes mcause value. */
final case class RAISE(exc: Int) extends Prim
