package sic

import org.scalatest.funsuite.AnyFunSuite
import sic.catalogue.SIC

/** Sanity test: catalogue must at least contain the currently stubbed entries.
  * Replace the lower‑bound with `== 47` once RV32I is fully entered.
  */
class CatalogueSpec extends AnyFunSuite {
  test("catalogue is defined") {
    assert(SIC.catalogue != null)
  }
  test("RV32I catalogue size placeholder") {
    assert(SIC.catalogue.size >= 4) // update to == 47 when complete
  }
}
