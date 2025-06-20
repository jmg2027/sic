package sic

/** Encodings recognised by the RISC‑V base ISA decoder.
  *
  * This enumeration is *pure metadata*: no behaviour is attached. It is
  * deliberately minimal; C‑extension formats (CR/CI/CB/…) may be added when RVC
  * support is enabled.
  *
  * ==Mapping==
  *   - R  → funct7|rs2|rs1|funct3|rd|opcode
  *   - I  → imm[11:0]|rs1|funct3|rd|opcode
  *   - S  → imm[11:5]|rs2|rs1|funct3|imm[4:0]|opcode
  *   - B  → imm[12|10:5]|rs2|rs1|funct3|imm[4:1|11]|opcode
  *   - U  → imm[31:12]|rd|opcode
  *   - UJ → imm[20|10:1|11|19:12]|rd|opcode
  */
sealed trait Format
case object R extends Format
case object I extends Format
case object S extends Format
case object B extends Format
case object U extends Format
case object UJ extends Format
case object CSR extends Format
