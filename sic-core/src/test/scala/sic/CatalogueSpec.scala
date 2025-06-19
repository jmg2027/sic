package sic

import org.scalatest.funsuite.AnyFunSuite
import sic.catalogue.SIC

class CatalogueSpec extends AnyFunSuite {
  test("catalogue is defined") {
    assert(SIC.catalogue != null)
  }
}
