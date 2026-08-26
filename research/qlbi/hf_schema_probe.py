#!/usr/bin/env python3
"""Probe selected SEC N-PORT mirror schemas and accession-local samples."""
from __future__ import annotations
import json
from pathlib import Path
import duckdb

YEAR=2026
QUARTER=2
ACCESSIONS=("0002071691-26-010941","0002071691-26-010957")
TABLES=("IDENTIFIERS","FUND_REPORTED_INFO","SUBMISSION","REGISTRANT")


def jsonable(v):
    if hasattr(v,"isoformat"):
        return v.isoformat()
    return str(v) if v is not None else None


def main():
    out=Path("qlbi_probe")
    out.mkdir(parents=True,exist_ok=True)
    con=duckdb.connect()
    try:
        con.execute("INSTALL httpfs")
    except Exception:
        pass
    con.execute("LOAD httpfs")
    result={}
    quoted=','.join("'"+x+"'" for x in ACCESSIONS)
    for table in TABLES:
        uri=f"hf://datasets/trader298/sec-nport/{table}/year={YEAR}/quarter={QUARTER}/data.parquet"
        desc=con.execute(f"DESCRIBE SELECT * FROM read_parquet('{uri}', hive_partitioning=true)").fetchall()
        cols=[r[0] for r in desc]
        sample=[]
        if "ACCESSION_NUMBER" in cols:
            rel=con.execute(f"SELECT * FROM read_parquet('{uri}', hive_partitioning=true) WHERE ACCESSION_NUMBER IN ({quoted}) LIMIT 50")
            rows=rel.fetchall()
            rcols=[d[0] for d in rel.description]
            sample=[{c:jsonable(v) for c,v in zip(rcols,row)} for row in rows]
        result[table]={"uri":uri,"description":[list(map(jsonable,r)) for r in desc],"columns":cols,"sample":sample}
    (out/"schemas_and_samples.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({k:{"columns":v["columns"],"sample_rows":len(v["sample"])} for k,v in result.items()},indent=2))

if __name__=="__main__":
    main()
