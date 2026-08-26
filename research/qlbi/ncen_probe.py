#!/usr/bin/env python3
"""Probe official SEC Form N-CEN quarterly flat-file archives.

Downloads recent official SEC archives with a declared User-Agent, records the
archive hashes, file names, delimiters, headers and a few rows. No inference is
performed. This establishes the exact series/adviser bridge schema before the
cross-manager null is rebuilt at parent-manager level.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
import zipfile
from pathlib import Path

import requests

QUARTERS = ("2025q1", "2025q2", "2025q3", "2025q4", "2026q1", "2026q2")
BASE = "https://www.sec.gov/files/dera/data/form-n-cen-data-sets"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def detect_delimiter(text: str) -> str:
    sample = text[:20000]
    try:
        return csv.Sniffer().sniff(sample, delimiters="\t,|").delimiter
    except csv.Error:
        return "\t"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="qlbi_ncen_probe")
    parser.add_argument("--email", default="research-contact@example.com")
    args = parser.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": f"QLBI academic research {args.email}",
        "Accept-Encoding": "gzip, deflate",
    }
    manifest = {
        "authority": "U.S. SEC Form N-CEN quarterly structured data",
        "quarters": {},
        "notes": [
            "Official SEC data files are authoritative and retained by SHA-256.",
            "The SEC data page states schema-version 3.1 filings may be absent from current structured datasets.",
        ],
    }
    for quarter in QUARTERS:
        url = f"{BASE}/{quarter}_ncen.zip"
        archive = outdir / f"{quarter}_ncen.zip"
        response = requests.get(url, headers=headers, timeout=180)
        response.raise_for_status()
        archive.write_bytes(response.content)
        quarter_info = {
            "url": url,
            "size_bytes": archive.stat().st_size,
            "sha256": sha256(archive),
            "files": {},
        }
        with zipfile.ZipFile(archive) as zf:
            for info in sorted(zf.infolist(), key=lambda item: item.filename):
                if info.is_dir():
                    continue
                raw = zf.read(info.filename)
                item = {
                    "size_bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
                lower = info.filename.lower()
                if lower.endswith((".tsv", ".csv", ".txt")):
                    text = raw.decode("utf-8-sig", errors="replace")
                    delimiter = detect_delimiter(text)
                    reader = csv.reader(text.splitlines(), delimiter=delimiter)
                    rows = []
                    for index, row in enumerate(reader):
                        rows.append(row)
                        if index >= 3:
                            break
                    item["delimiter"] = "TAB" if delimiter == "\t" else delimiter
                    item["header"] = rows[0] if rows else []
                    item["sample_rows"] = rows[1:]
                quarter_info["files"][info.filename] = item
        manifest["quarters"][quarter] = quarter_info
        time.sleep(0.25)
    (outdir / "schema_probe.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
