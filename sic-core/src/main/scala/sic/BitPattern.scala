package sic

final case class BitPattern(mask: BigInt, value: BigInt)

object BitPattern {
  def from(opcode: Int, nBits: Int): BitPattern = {
    val mask = (BigInt(1) << nBits) - 1
    val value = BigInt(opcode)
    BitPattern(mask, value)
  }
}
