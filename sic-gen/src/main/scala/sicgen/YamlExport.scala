package sicgen
import sic.catalogue.SIC
import io.circe.syntax.*
import io.circe.yaml.syntax.*

object YamlExport extends App {
  println(SIC.catalogue.asYaml.spaces2)
}
