package sic

/** Hardware‑friendly (mask,value) pair used for fast opcode matching.
  *
  * ==Definition==
  * For a candidate instruction word `x` and pattern `(m,v)`: matches ⇔ (x & m)
  * \== v
  *
  * ==Usage==
  * The 7‑bit opcode pattern for `LUI` (`0110111`) becomes `mask = 0x7F`, `value
  * \= 0x37`.
  */
final case class BitPattern(mask: BigInt, value: BigInt) {

  /** True if `bits` satisfies this pattern. */
  def matches(bits: BigInt): Boolean = (bits & mask) == value
}

object BitPattern {

  /** Construct pattern with full‑width mask (all 1s).
    * @param value
    *   numeric value
    * @param width
    *   bit‑width, e.g. 7
    */
  def fromWidth(value: BigInt, width: Int): BitPattern =
    BitPattern(mask = (BigInt(1) << width) - 1, value = value)
}
