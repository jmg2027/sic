#!/usr/bin/env python3
"""Longitudinal two-sided cash-equity validation for two AQR sibling funds.

Only paired report dates on which both series have directly observed EC long
and short positions enter the validation sample. One-sided or empty dates are
retained in exclusions.csv with an explicit reason. Direct short exposure is
not interpreted as negative-alpha intent.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

BASE = "hf://datasets/trader298/sec-nport"
SERIES_A = "S000046740"
SERIES_B = "S000041116"
SERIES_NAMES = {
    SERIES_A: "AQR Equity Market Neutral Fund",
    SERIES_B: "AQR Long-Short Equity Fund",
}
NULLS = {"", "N/A", "NA", "NONE", "NULL", "NOT AVAILABLE"}


class StudyError(RuntimeError):
    pass


def clean(value: Any) -> str | None:
    if value is None:
        return None
    out = str(value).strip()
    return None if out.upper() in NULLS else out


def fnum(value: Any) -> float:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return 0.0
    return out if math.isfinite(out) else 0.0


def security_key(cusip: Any, country: Any, issuer: Any, title: Any) -> str:
    c = re.sub(r"[^A-Za-z0-9]", "", clean(cusip) or "").upper()
    if 6 <= len(c) <= 12:
        return "CUSIP:" + c
    cc = re.sub(r"[^A-Za-z0-9]", "", clean(country) or "XX").upper() or "XX"
    name = re.sub(r"[^A-Za-z0-9]+", " ", clean(issuer) or clean(title) or "").upper().strip()
    if not name:
        raise StudyError("Unkeyed holding")
    return f"NAME:{cc}:{name}"


def partitions(table: str) -> list[str]:
    out: list[str] = []
    for year in range(2019, 2027):
        qs = [4] if year == 2019 else ([1, 2] if year == 2026 else [1, 2, 3, 4])
        for quarter in qs:
            out.append(f"{BASE}/{table}/year={year}/quarter={quarter}/data.parquet")
    return out


def sql_list(values: list[str]) -> str:
    return "[" + ",".join("'" + value.replace("'", "''") + "'" for value in values) + "]"


def corr_dict(a: dict[str, float], b: dict[str, float], rank: bool = False) -> float | None:
    keys = sorted(set(a) | set(b))
    if len(keys) < 3:
        return None
    x = np.array([a.get(key, 0.0) for key in keys], dtype=float)
    y = np.array([b.get(key, 0.0) for key in keys], dtype=float)
    if rank:
        x = pd.Series(x).rank(method="average").to_numpy(dtype=float)
        y = pd.Series(y).rank(method="average").to_numpy(dtype=float)
    if np.std(x) <= 0 or np.std(y) <= 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def weighted_jaccard(a: dict[str, float], b: dict[str, float]) -> float:
    keys = set(a) | set(b)
    denominator = sum(max(a.get(key, 0.0), b.get(key, 0.0)) for key in keys)
    return (
        sum(min(a.get(key, 0.0), b.get(key, 0.0)) for key in keys) / denominator
        if denominator > 0
        else 0.0
    )


def support_jaccard(a: dict[str, float], b: dict[str, float]) -> float:
    aa = {key for key, value in a.items() if value > 0}
    bb = {key for key, value in b.items() if value > 0}
    return len(aa & bb) / len(aa | bb) if aa | bb else 0.0


def country_residual(book: dict[str, dict[str, Any]]) -> dict[str, float]:
    net: dict[str, float] = defaultdict(float)
    activity: dict[str, float] = defaultdict(float)
    for row in book.values():
        net[row["country"]] += row["signed"]
        activity[row["country"]] += row["activity"]
    return {
        key: row["signed"]
        - (
            net[row["country"]] * row["activity"] / activity[row["country"]]
            if activity[row["country"]] > 0
            else 0.0
        )
        for key, row in book.items()
    }


def load_metadata(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    fund_uris = sql_list(partitions("FUND_REPORTED_INFO"))
    submission_uris = sql_list(partitions("SUBMISSION"))
    query = f"""
    WITH f AS (
      SELECT ACCESSION_NUMBER, SERIES_NAME, SERIES_ID, year, quarter
      FROM read_parquet({fund_uris}, hive_partitioning=true, union_by_name=true)
      WHERE SERIES_ID IN ('{SERIES_A}', '{SERIES_B}')
    ), s AS (
      SELECT ACCESSION_NUMBER, REPORT_DATE, FILING_DATE, SUB_TYPE, year, quarter
      FROM read_parquet({submission_uris}, hive_partitioning=true, union_by_name=true)
      WHERE SUB_TYPE='NPORT-P'
    )
    SELECT f.*, s.REPORT_DATE, s.FILING_DATE
    FROM f JOIN s USING (ACCESSION_NUMBER, year, quarter)
    ORDER BY REPORT_DATE, SERIES_ID, FILING_DATE, ACCESSION_NUMBER
    """
    frame = con.execute(query).fetchdf()
    frame["REPORT_DATE"] = pd.to_datetime(frame["REPORT_DATE"])
    frame["FILING_DATE"] = pd.to_datetime(frame["FILING_DATE"])
    frame = (
        frame.sort_values(["REPORT_DATE", "SERIES_ID", "FILING_DATE", "ACCESSION_NUMBER"])
        .drop_duplicates(["REPORT_DATE", "SERIES_ID"], keep="first")
    )
    paired = frame.groupby("REPORT_DATE")["SERIES_ID"].nunique()
    return frame[frame["REPORT_DATE"].isin(set(paired[paired == 2].index))].copy()


def load_partition_holdings(
    con: duckdb.DuckDBPyConnection,
    year: int,
    quarter: int,
    accessions: list[str],
) -> pd.DataFrame:
    uri = f"{BASE}/FUND_REPORTED_HOLDING/year={year}/quarter={quarter}/data.parquet"
    quoted = ",".join("'" + accession.replace("'", "''") + "'" for accession in accessions)
    return con.execute(
        f"""
        SELECT ACCESSION_NUMBER, ISSUER_NAME, ISSUER_TITLE, ISSUER_CUSIP,
               INVESTMENT_COUNTRY, PAYOFF_PROFILE, abs(CURRENCY_VALUE) AS value_usd
        FROM read_parquet('{uri}', hive_partitioning=true)
        WHERE ACCESSION_NUMBER IN ({quoted})
          AND upper(ASSET_CAT)='EC'
          AND upper(PAYOFF_PROFILE) IN ('LONG','SHORT')
        """
    ).fetchdf()


def build_book(rows: pd.DataFrame, accession: str) -> tuple[dict[str, dict[str, Any]] | None, dict[str, Any]]:
    raw: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"long": 0.0, "short": 0.0, "country": "XX"}
    )
    subset = rows[rows["ACCESSION_NUMBER"] == accession]
    for row in subset.itertuples(index=False):
        key = security_key(row.ISSUER_CUSIP, row.INVESTMENT_COUNTRY, row.ISSUER_NAME, row.ISSUER_TITLE)
        record = raw[key]
        record["country"] = clean(row.INVESTMENT_COUNTRY) or "XX"
        record["long" if str(row.PAYOFF_PROFILE).upper() == "LONG" else "short"] += fnum(row.value_usd)
    gross_long = sum(record["long"] for record in raw.values())
    gross_short = sum(record["short"] for record in raw.values())
    diagnostics = {
        "accession": accession,
        "row_count": int(len(subset)),
        "unique_securities": int(len(raw)),
        "gross_long_usd": gross_long,
        "gross_short_usd": gross_short,
        "long_count": int(sum(record["long"] > 0 for record in raw.values())),
        "short_count": int(sum(record["short"] > 0 for record in raw.values())),
    }
    if gross_long <= 0 or gross_short <= 0:
        diagnostics["eligible_two_sided"] = False
        diagnostics["exclusion_reason"] = (
            "NO_EC_ROWS" if len(subset) == 0 else "ONE_SIDED_EC_BOOK"
        )
        return None, diagnostics
    book: dict[str, dict[str, Any]] = {}
    for key, record in raw.items():
        w_long = record["long"] / gross_long
        w_short = record["short"] / gross_short
        book[key] = {
            **record,
            "w_long": w_long,
            "w_short": w_short,
            "signed": w_long - w_short,
            "activity": 0.5 * (w_long + w_short),
        }
    diagnostics["eligible_two_sided"] = True
    return book, diagnostics


def metrics(a: dict[str, dict[str, Any]], b: dict[str, dict[str, Any]]) -> dict[str, Any]:
    signed_a = {key: row["signed"] for key, row in a.items()}
    signed_b = {key: row["signed"] for key, row in b.items()}
    country_a = country_residual(a)
    country_b = country_residual(b)
    long_a = {key: row["w_long"] for key, row in a.items() if row["w_long"] > 0}
    long_b = {key: row["w_long"] for key, row in b.items() if row["w_long"] > 0}
    short_a = {key: row["w_short"] for key, row in a.items() if row["w_short"] > 0}
    short_b = {key: row["w_short"] for key, row in b.items() if row["w_short"] > 0}
    shared = set(a) & set(b)
    all_keys = set(a) | set(b)
    x = np.array([signed_a.get(key, 0.0) for key in all_keys])
    y = np.array([signed_b.get(key, 0.0) for key in all_keys])
    denominator = 0.5 * (np.sum(x * x) + np.sum(y * y))
    same_activity = sum(
        min(a[key]["activity"], b[key]["activity"])
        for key in shared
        if signed_a[key] * signed_b[key] >= 0
    )
    shared_activity = sum(min(a[key]["activity"], b[key]["activity"]) for key in shared)
    return {
        "union_count": len(all_keys),
        "shared_count": len(shared),
        "signed_pearson": corr_dict(signed_a, signed_b),
        "signed_spearman": corr_dict(signed_a, signed_b, rank=True),
        "country_neutral_pearson": corr_dict(country_a, country_b),
        "country_neutral_spearman": corr_dict(country_a, country_b, rank=True),
        "long_weighted_jaccard": weighted_jaccard(long_a, long_b),
        "short_weighted_jaccard": weighted_jaccard(short_a, short_b),
        "long_support_jaccard": support_jaccard(long_a, long_b),
        "short_support_jaccard": support_jaccard(short_a, short_b),
        "long_common_mass": sum(min(long_a.get(key, 0), long_b.get(key, 0)) for key in set(long_a) | set(long_b)),
        "short_common_mass": sum(min(short_a.get(key, 0), short_b.get(key, 0)) for key in set(short_a) | set(short_b)),
        "common_energy_share": float(np.sum((0.5 * (x + y)) ** 2) / denominator) if denominator > 0 else None,
        "opposite_side_rate": (
            sum(signed_a[key] * signed_b[key] < 0 for key in shared) / len(shared)
            if shared
            else None
        ),
        "weighted_same_side_rate": same_activity / shared_activity if shared_activity > 0 else None,
    }


def delta_vector(current: dict[str, dict[str, Any]], previous: dict[str, dict[str, Any]]) -> dict[str, float]:
    return {
        key: current.get(key, {}).get("signed", 0.0) - previous.get(key, {}).get("signed", 0.0)
        for key in set(current) | set(previous)
    }


def summarize(values: list[Any]) -> dict[str, Any]:
    array = np.array([float(value) for value in values if value is not None and math.isfinite(float(value))])
    if len(array) == 0:
        return {"n": 0, "median": None, "p10": None, "p90": None, "min": None, "max": None}
    return {
        "n": int(len(array)),
        "median": float(np.median(array)),
        "p10": float(np.quantile(array, 0.10)),
        "p90": float(np.quantile(array, 0.90)),
        "min": float(np.min(array)),
        "max": float(np.max(array)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="qlbi_aqr_longitudinal")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs")
    except Exception:
        pass
    con.execute("LOAD httpfs")

    metadata = load_metadata(con)
    accepted: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    books_by_date: dict[pd.Timestamp, tuple[dict[str, Any], dict[str, Any]]] = {}

    for report_date, group in metadata.groupby("REPORT_DATE"):
        accession_by_series = dict(zip(group["SERIES_ID"], group["ACCESSION_NUMBER"]))
        frames: list[pd.DataFrame] = []
        for (year, quarter), partition_group in group.groupby(["year", "quarter"]):
            frames.append(
                load_partition_holdings(
                    con,
                    int(year),
                    int(quarter),
                    partition_group["ACCESSION_NUMBER"].tolist(),
                )
            )
        rows = pd.concat(frames, ignore_index=True)
        book_a, diag_a = build_book(rows, accession_by_series[SERIES_A])
        book_b, diag_b = build_book(rows, accession_by_series[SERIES_B])
        if book_a is None or book_b is None:
            exclusions.append(
                {
                    "report_date": str(pd.Timestamp(report_date).date()),
                    "a_accession": accession_by_series[SERIES_A],
                    "b_accession": accession_by_series[SERIES_B],
                    "a_reason": diag_a.get("exclusion_reason"),
                    "b_reason": diag_b.get("exclusion_reason"),
                    "a_long_count": diag_a["long_count"],
                    "a_short_count": diag_a["short_count"],
                    "b_long_count": diag_b["long_count"],
                    "b_short_count": diag_b["short_count"],
                }
            )
            continue
        row = metrics(book_a, book_b)
        row.update(
            {
                "report_date": str(pd.Timestamp(report_date).date()),
                "a_accession": accession_by_series[SERIES_A],
                "b_accession": accession_by_series[SERIES_B],
                "a_long_count": diag_a["long_count"],
                "a_short_count": diag_a["short_count"],
                "b_long_count": diag_b["long_count"],
                "b_short_count": diag_b["short_count"],
                "gross_long_scale_b_over_a": diag_b["gross_long_usd"] / diag_a["gross_long_usd"],
                "gross_short_scale_b_over_a": diag_b["gross_short_usd"] / diag_a["gross_short_usd"],
            }
        )
        accepted.append(row)
        books_by_date[pd.Timestamp(report_date)] = (book_a, book_b)

    accepted.sort(key=lambda row: row["report_date"])
    for index, row in enumerate(accepted):
        if index == 0:
            row["delta_signed_pearson"] = None
            row["delta_signed_spearman"] = None
            row["common_inventory_persistence"] = None
            continue
        previous_date = pd.Timestamp(accepted[index - 1]["report_date"])
        current_date = pd.Timestamp(row["report_date"])
        previous_a, previous_b = books_by_date[previous_date]
        current_a, current_b = books_by_date[current_date]
        delta_a = delta_vector(current_a, previous_a)
        delta_b = delta_vector(current_b, previous_b)
        common_previous = {
            key: 0.5 * (
                previous_a.get(key, {}).get("signed", 0.0)
                + previous_b.get(key, {}).get("signed", 0.0)
            )
            for key in set(previous_a) | set(previous_b)
        }
        common_current = {
            key: 0.5 * (
                current_a.get(key, {}).get("signed", 0.0)
                + current_b.get(key, {}).get("signed", 0.0)
            )
            for key in set(current_a) | set(current_b)
        }
        row["delta_signed_pearson"] = corr_dict(delta_a, delta_b)
        row["delta_signed_spearman"] = corr_dict(delta_a, delta_b, rank=True)
        row["common_inventory_persistence"] = corr_dict(common_previous, common_current)

    if len(accepted) < 4:
        raise StudyError(f"Too few eligible paired two-sided dates: {len(accepted)}")

    metrics_frame = pd.DataFrame(accepted)
    metrics_frame.to_csv(outdir / "quarterly_metrics.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(exclusions).to_csv(outdir / "excluded_dates.csv", index=False)
    metadata.to_csv(outdir / "all_paired_filing_metadata.csv", index=False)

    monitored = [
        "signed_pearson",
        "signed_spearman",
        "country_neutral_pearson",
        "long_weighted_jaccard",
        "short_weighted_jaccard",
        "long_common_mass",
        "short_common_mass",
        "common_energy_share",
        "weighted_same_side_rate",
        "delta_signed_pearson",
        "delta_signed_spearman",
        "common_inventory_persistence",
    ]
    summary = {column: summarize(metrics_frame[column].tolist()) for column in monitored}
    high_level_dates = int((metrics_frame["signed_pearson"] >= 0.80).sum())
    median_delta = summary["delta_signed_pearson"]["median"]
    gate = (
        "LONGITUDINAL_COMMON_ENGINE_PASS"
        if len(metrics_frame) >= 8
        and high_level_dates / len(metrics_frame) >= 0.80
        and median_delta is not None
        and median_delta >= 0.50
        else "LONGITUDINAL_GATE_FAIL_OR_INCONCLUSIVE"
    )
    result = {
        "status": "EXECUTED",
        "gate": gate,
        "all_paired_report_dates": int(metadata["REPORT_DATE"].nunique()),
        "eligible_two_sided_report_dates": int(len(metrics_frame)),
        "excluded_report_dates": int(len(exclusions)),
        "first_eligible_report_date": metrics_frame["report_date"].min(),
        "last_eligible_report_date": metrics_frame["report_date"].max(),
        "dates_signed_pearson_ge_0_80": high_level_dates,
        "summary": summary,
        "provenance": {
            "authority": "U.S. SEC Form N-PORT quarterly structured data",
            "transport": "trader298/sec-nport typed Parquet mirror",
            "two_sided_gate": "both series must have directly observed EC long and EC short on the report date",
            "direct_short_is_exposure_not_intent": True,
        },
        "limitations": [
            "Derivative overlays are excluded.",
            "This is structural validation, not an OOS return test.",
            "Skipping one-sided dates changes the estimand to the period in which both products operate two-sided cash books.",
        ],
    }
    (outdir / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# QLBI AQR longitudinal two-sided validation",
        "",
        f"Gate: `{gate}`",
        "",
        f"Eligible dates: {len(metrics_frame)}; excluded paired dates: {len(exclusions)}.",
        "",
        "| Metric | N | Median | P10 | Min | Max |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for column in monitored:
        value = summary[column]
        lines.append(
            f"| {column} | {value['n']} | {value['median']} | {value['p10']} | {value['min']} | {value['max']} |"
        )
    lines += [
        "",
        "Observed shorts are direct economic exposures, not automatically bearish intent.",
        "One-sided dates are preserved in excluded_dates.csv rather than silently coerced.",
    ]
    (outdir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
