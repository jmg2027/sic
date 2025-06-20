// src/main/scala/sic/FormatFields.scala
package sic
import sic.FieldRange

/** Static lookup‑table: format → default bit‑ranges. */
object FormatFields {
  val table: Map[Format, Map[String, FieldRange]] = Map(
    R -> Map(
      "funct7" -> FieldRange(31, 25),
      "rs2" -> FieldRange(24, 20),
      "rs1" -> FieldRange(19, 15),
      "funct3" -> FieldRange(14, 12),
      "rd" -> FieldRange(11, 7)
    ),
    I -> Map(
      "imm" -> FieldRange(31, 20),
      "rs1" -> FieldRange(19, 15),
      "funct3" -> FieldRange(14, 12),
      "rd" -> FieldRange(11, 7)
    ),
    S -> Map(
      "imm_hi" -> FieldRange(31, 25),
      "rs2" -> FieldRange(24, 20),
      "rs1" -> FieldRange(19, 15),
      "funct3" -> FieldRange(14, 12),
      "imm_lo" -> FieldRange(11, 7)
    ),
    B -> Map(
      "imm12" -> FieldRange(31, 31),
      "imm10_5" -> FieldRange(30, 25),
      "rs2" -> FieldRange(24, 20),
      "rs1" -> FieldRange(19, 15),
      "funct3" -> FieldRange(14, 12),
      "imm4_1" -> FieldRange(11, 8),
      "imm11" -> FieldRange(7, 7)
    ),
    U -> Map("imm" -> FieldRange(31, 12), "rd" -> FieldRange(11, 7)),
    UJ -> Map(
      "imm20" -> FieldRange(31, 31),
      "imm10_1" -> FieldRange(30, 21),
      "imm11" -> FieldRange(20, 20),
      "imm19_12" -> FieldRange(19, 12),
      "rd" -> FieldRange(11, 7)
    )
  )
}
