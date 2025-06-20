package sicgen

import sic.catalogue.SIC
import io.circe.syntax._
import io.circe.yaml.syntax._
import io.circe.generic.auto._

import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets

/** ===YAML Dump Utility===
  *
  * Writes the current **Semantic Instruction Catalogue (SIC)** to
  *  `generated/sic.yaml` so non‑Scala tools (e.g. Sail trace diff,
  *  documentation build) can consume the same single source of truth.
  *
  *  - The file path is fixed (`generated/`) to keep `.gitignore` simple.  -
  * Over‑writes on every run; CI can diff in pull‑requests.
  *
  * ====Usage (from shell)====
  * {{{
  *   sbt "sicGen/runMain sicgen.YamlExport"
  * }}}
  *
  * ====Output example====
  * ```yaml
  * - name: JAL
  *   format: UJ
  *   decodeKey: { mask: 0x7F, value: 0x6F }
  *   ...
  * ```
  */
object YamlExport extends App {

  /** Serialise the catalogue to YAML (2‑space indentation). */
  private val yaml: String = SIC.catalogue.asJson.asYaml.spaces2

  /** Output location (`generated/sic.yaml`). */
  private val path = Paths.get("generated", "sic.yaml")

  Files.createDirectories(path.getParent)
  Files.write(path, yaml.getBytes(StandardCharsets.UTF_8))
  println(s"Wrote $path")
}
