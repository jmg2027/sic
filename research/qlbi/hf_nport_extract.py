#!/usr/bin/env python3
"""Extract two AQR N-PORT filings from the public SEC-NPORT Parquet mirror.

The mirror is a typed, partitioned copy of the SEC quarterly N-PORT flat files.
This adapter does not alter the filing accession or holding values. It emits a
minimal XML representation containing only fields consumed by the stock-book
pilot, plus the exact flat rows, schema, and provenance hashes.

This exists because SEC EDGAR may reject GitHub-hosted runners with HTTP 403.
The SEC filing remains authoritative; the mirror is a transport layer only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable
import xml.etree.ElementTree as ET

import duckdb

DATASET = "trader298/sec-nport"
TABLE = "FUND_REPORTED_HOLDING"
PARTITION_YEAR = 2026
PARTITION_QUARTER = 2
PARQUET_URI = (
    "hf://datasets/trader298/sec-nport/"
    "FUND_REPORTED_HOLDING/year=2026/quarter=2/data.parquet"
)
TARGETS = {
    "0002071691-26-010941": {
        "filename": "market_neutral.xml",
        "series_name": "AQR Equity Market Neutral Fund",
        "series_id": "S000046740",
    },
    "0002071691-26-010957": {
        "filename": "long_short.xml",
        "series_name": "AQR Long-Short Equity Fund",
        "series_id": "S000041116",
    },
}
REPORT_DATE = "2026-03-31"
REGISTRANT = "AQR Funds"


class ExtractError(RuntimeError):
    """Expected, fail-closed extraction error."""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    return value


def normalized_columns(columns: Iterable[str]) -> dict[str, str]:
    return {str(column).strip().upper(): str(column) for column in columns}


def choose(columns: dict[str, str], *aliases: str, required: bool = True) -> str | None:
    for alias in aliases:
        found = columns.get(alias.upper())
        if found is not None:
            return found
    if required:
        raise ExtractError(
            "Required column missing; expected one of "
            + ", ".join(aliases)
            + "; available="
            + ", ".join(sorted(columns))
        )
    return None


def text(value: Any) -> str | None:
    if value is None:
        return None
    out = str(value).strip()
    return out if out and out.upper() not in {"N/A", "NA", "NULL", "NONE"} else None


def numeric_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return format(value, ".17g")
    return str(value)


def add(parent: ET.Element, tag: str, value: Any) -> None:
    value_text = text(value)
    if value_text is None:
        return
    ET.SubElement(parent, tag).text = value_text


def write_rows_csv(path: Path, columns: list[str], rows: list[tuple[Any, ...]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for row in rows:
            writer.writerow([json_value(value) for value in row])


def build_minimal_xml(
    path: Path,
    accession: str,
    target: dict[str, str],
    columns: list[str],
    rows: list[tuple[Any, ...]],
    field_map: dict[str, str | None],
) -> dict[str, Any]:
    index = {column: position for position, column in enumerate(columns)}

    def get(row: tuple[Any, ...], logical: str) -> Any:
        column = field_map.get(logical)
        return row[index[column]] if column is not None else None

    root = ET.Element("edgarSubmission")
    form = ET.SubElement(root, "formData")
    gen = ET.SubElement(form, "genInfo")
    add(gen, "regName", REGISTRANT)
    add(gen, "seriesName", target["series_name"])
    add(gen, "seriesId", target["series_id"])
    add(gen, "repPdDate", REPORT_DATE)
    add(gen, "repPdEnd", REPORT_DATE)
    # The stock-book pilot does not use fund balance-sheet fields. Keep the
    # structural node present and omit unknown values rather than fabricating.
    ET.SubElement(form, "fundInfo")
    securities = ET.SubElement(form, "invstOrSecs")

    payoff_counts: Counter[str] = Counter()
    asset_counts: Counter[str] = Counter()
    country_counts: Counter[str] = Counter()
    cash_long = 0
    cash_short = 0
    emitted = 0

    for row in rows:
        inv = ET.SubElement(securities, "invstOrSec")
        add(inv, "name", get(row, "name"))
        add(inv, "title", get(row, "title"))
        add(inv, "cusip", get(row, "cusip"))
        add(inv, "lei", get(row, "lei"))
        add(inv, "balance", numeric_text(get(row, "balance")))
        add(inv, "units", get(row, "unit"))
        add(inv, "curCd", get(row, "currency_code"))
        add(inv, "valUSD", numeric_text(get(row, "currency_value")))
        add(inv, "pctVal", numeric_text(get(row, "percentage_value")))
        add(inv, "payoffProfile", get(row, "payoff_profile"))
        add(inv, "assetCat", get(row, "asset_category"))
        add(inv, "issuerCat", get(row, "issuer_category"))
        add(inv, "invCountry", get(row, "country"))
        add(inv, "fairValLevel", get(row, "fair_value_level"))
        add(inv, "isRestrictedSec", get(row, "restricted"))

        identifiers = ET.SubElement(inv, "identifiers")
        ticker = get(row, "ticker")
        isin = get(row, "isin")
        if text(ticker) is not None:
            ET.SubElement(identifiers, "ticker", {"value": text(ticker) or ""})
        if text(isin) is not None:
            ET.SubElement(identifiers, "isin", {"value": text(isin) or ""})
        if len(identifiers) == 0:
            inv.remove(identifiers)

        payoff = (text(get(row, "payoff_profile")) or "").upper()
        asset = (text(get(row, "asset_category")) or "").upper()
        country = text(get(row, "country")) or "__MISSING__"
        payoff_counts[payoff or "__MISSING__"] += 1
        asset_counts[asset or "__MISSING__"] += 1
        country_counts[country] += 1
        if asset == "EC" and payoff == "LONG":
            cash_long += 1
        if asset == "EC" and payoff == "SHORT":
            cash_short += 1
        emitted += 1

    if emitted < 100:
        raise ExtractError(f"Accession {accession} yielded only {emitted} holding rows")
    if cash_long == 0 or cash_short == 0:
        raise ExtractError(
            f"Accession {accession} lacks both EC sides: long_rows={cash_long}, short_rows={cash_short}"
        )

    ET.indent(root, space="  ")
    ET.ElementTree(root).write(path, encoding="utf-8", xml_declaration=True)
    return {
        "accession": accession,
        "series_name": target["series_name"],
        "series_id": target["series_id"],
        "report_date": REPORT_DATE,
        "holding_rows": emitted,
        "ec_long_rows": cash_long,
        "ec_short_rows": cash_short,
        "payoff_counts": dict(payoff_counts),
        "asset_category_counts": dict(asset_counts),
        "top_countries": dict(country_counts.most_common(20)),
        "xml_filename": path.name,
        "xml_sha256": sha256(path),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="qlbi_source")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect()
    # DuckDB's hf:// filesystem uses the httpfs extension. LOAD is harmless if
    # already available in the bundled DuckDB distribution.
    try:
        connection.execute("INSTALL httpfs")
    except Exception:
        pass
    connection.execute("LOAD httpfs")

    # Read only the target accession rows; the mirror remains remote and the
    # selected flat rows are persisted locally for auditability.
    quoted = ",".join("'" + accession.replace("'", "''") + "'" for accession in TARGETS)
    relation = connection.execute(
        f"""
        SELECT *
        FROM read_parquet('{PARQUET_URI}', hive_partitioning=true)
        WHERE ACCESSION_NUMBER IN ({quoted})
        ORDER BY ACCESSION_NUMBER, HOLDING_ID
        """
    )
    rows = relation.fetchall()
    columns = [description[0] for description in relation.description]
    if not rows:
        raise ExtractError("No target accession rows returned from the Parquet mirror")

    column_lookup = normalized_columns(columns)
    accession_column = choose(column_lookup, "ACCESSION_NUMBER")
    holding_column = choose(column_lookup, "HOLDING_ID")
    field_map: dict[str, str | None] = {
        "accession": accession_column,
        "holding_id": holding_column,
        "name": choose(column_lookup, "ISSUER_NAME", "NAME"),
        "title": choose(column_lookup, "ISSUER_TITLE", "TITLE", required=False),
        "cusip": choose(column_lookup, "ISSUER_CUSIP", "CUSIP", required=False),
        "lei": choose(column_lookup, "ISSUER_LEI", "LEI", required=False),
        "balance": choose(column_lookup, "BALANCE", required=False),
        "unit": choose(column_lookup, "UNIT", "UNITS", required=False),
        "currency_code": choose(column_lookup, "CURRENCY_CODE", "CUR_CD", required=False),
        "currency_value": choose(column_lookup, "CURRENCY_VALUE", "VALUE_USD", "VAL_USD"),
        "percentage_value": choose(
            column_lookup, "PERCENTAGE_VALUE", "PCT_VALUE", "PCT_VAL", required=False
        ),
        "payoff_profile": choose(column_lookup, "PAYOFF_PROFILE"),
        "asset_category": choose(column_lookup, "ASSET_CAT", "ASSET_CATEGORY"),
        "issuer_category": choose(column_lookup, "ISSUER_CAT", "ISSUER_CATEGORY", required=False),
        "country": choose(
            column_lookup,
            "INVESTMENT_COUNTRY",
            "INV_COUNTRY",
            "COUNTRY",
            required=False,
        ),
        "fair_value_level": choose(column_lookup, "FAIR_VALUE_LEVEL", required=False),
        "restricted": choose(
            column_lookup, "IS_RESTRICTED_SECURITY", "IS_RESTRICTED_SEC", required=False
        ),
        # Ticker/ISIN normally live in the IDENTIFIERS table. CUSIP is enough
        # for this pilot, so these are optional and remain absent unless the
        # mirror later denormalizes them into the holding table.
        "ticker": choose(column_lookup, "TICKER", required=False),
        "isin": choose(column_lookup, "ISIN", required=False),
    }

    (outdir / "schema.json").write_text(
        json.dumps(
            {
                "parquet_uri": PARQUET_URI,
                "columns": columns,
                "field_map": field_map,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    write_rows_csv(outdir / "target_holdings_flat.csv", columns, rows)

    position = {column: idx for idx, column in enumerate(columns)}
    by_accession: dict[str, list[tuple[Any, ...]]] = {key: [] for key in TARGETS}
    for row in rows:
        accession = text(row[position[accession_column]])
        if accession in by_accession:
            by_accession[accession].append(row)

    diagnostics: dict[str, Any] = {}
    for accession, target in TARGETS.items():
        filing_rows = by_accession[accession]
        if not filing_rows:
            raise ExtractError(f"Missing accession in mirror: {accession}")
        diagnostics[accession] = build_minimal_xml(
            outdir / target["filename"],
            accession,
            target,
            columns,
            filing_rows,
            field_map,
        )

    manifest = {
        "source_authority": "U.S. SEC Form N-PORT quarterly structured data",
        "transport_mirror": DATASET,
        "transport_mirror_status": "unofficial typed Parquet mirror",
        "table": TABLE,
        "partition": {"year": PARTITION_YEAR, "quarter": PARTITION_QUARTER},
        "parquet_uri": PARQUET_URI,
        "target_accessions": list(TARGETS),
        "report_date": REPORT_DATE,
        "row_count": len(rows),
        "flat_extract_sha256": sha256(outdir / "target_holdings_flat.csv"),
        "schema_sha256": sha256(outdir / "schema.json"),
        "field_map": field_map,
        "filings": diagnostics,
        "limitations": [
            "The mirror is a transport layer; SEC source filings remain authoritative.",
            "The adapter emits only fields required for direct cash-equity comparison.",
            "Ticker and ISIN are not joined from the separate IDENTIFIERS table in this pilot.",
            "A direct short exposure is not automatically a negative-alpha view.",
        ],
    }
    (outdir / "SOURCE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, default=json_value) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False, default=json_value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
