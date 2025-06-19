package sicgen
import sic.catalogue.SIC
import io.circe.syntax._
import io.circe.yaml.syntax._
import io.circe.generic.auto._

import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets

object YamlExport extends App {
  val yaml = SIC.catalogue.asJson.asYaml.spaces2
  val path = Paths.get("generated", "sic.yaml")
  Files.createDirectories(path.getParent)
  Files.write(path, yaml.getBytes(StandardCharsets.UTF_8))
  println(s"Wrote $path")
}
