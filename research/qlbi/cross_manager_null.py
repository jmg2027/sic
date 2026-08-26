#!/usr/bin/env python3
"""Same-date cross-manager null for the AQR sibling stock-book result.

Uses only direct cash-equity long/short Form N-PORT rows. It identifies all
2026-03-31 filings with sufficiently broad two-sided EC books, matches them on
book breadth, gross balance and country composition, then compares the AQR
sibling similarity with unrelated-registrant pairs. Direct short exposure is
not labelled as negative-alpha intent.
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

YEAR=2026
QUARTER=2
REPORT_DATE="2026-03-31"
BASE="hf://datasets/trader298/sec-nport"
HOLDINGS=f"{BASE}/FUND_REPORTED_HOLDING/year={YEAR}/quarter={QUARTER}/data.parquet"
FUND_INFO=f"{BASE}/FUND_REPORTED_INFO/year={YEAR}/quarter={QUARTER}/data.parquet"
SUBMISSION=f"{BASE}/SUBMISSION/year={YEAR}/quarter={QUARTER}/data.parquet"
REGISTRANT=f"{BASE}/REGISTRANT/year={YEAR}/quarter={QUARTER}/data.parquet"
AQR_A="0002071691-26-010941"
AQR_B="0002071691-26-010957"
AQR={AQR_A,AQR_B}
NULLS={"","N/A","NA","NONE","NULL","NOT AVAILABLE"}

class StudyError(RuntimeError):
    pass

def text(v: Any) -> str | None:
    if v is None: return None
    x=str(v).strip()
    return None if x.upper() in NULLS else x

def fnum(v: Any) -> float:
    try: x=float(v)
    except (TypeError,ValueError): return 0.0
    return x if math.isfinite(x) else 0.0

def norm_id(v: Any) -> str | None:
    x=text(v)
    if x is None: return None
    y=re.sub(r"[^A-Za-z0-9]","",x).upper()
    return y or None

def norm_name(v: Any) -> str:
    x=re.sub(r"[^A-Za-z0-9]+"," ",(text(v) or "").upper()).strip()
    suffix={"INC","INCORPORATED","CORP","CORPORATION","CO","COMPANY","LTD","LIMITED","PLC","SA","NV","AG","SE","LLC","LP"}
    return " ".join(part for part in x.split() if part not in suffix)

def security_key(cusip: Any,country: Any,name: Any,title: Any) -> str:
    c=norm_id(cusip)
    if c and 6<=len(c)<=12: return "CUSIP:"+c
    cc=norm_id(country) or "XX"
    n=norm_name(name or title)
    if not n: raise StudyError("holding has no usable key")
    return f"NAME:{cc}:{n}:{norm_name(title)[:24]}"

def pearson(x:list[float],y:list[float]) -> float | None:
    if len(x)!=len(y) or len(x)<3: return None
    mx=sum(x)/len(x); my=sum(y)/len(y)
    vx=sum((a-mx)**2 for a in x); vy=sum((b-my)**2 for b in y)
    if vx<=0 or vy<=0: return None
    return sum((a-mx)*(b-my) for a,b in zip(x,y))/math.sqrt(vx*vy)

def ranks(values:list[float]) -> list[float]:
    order=sorted(range(len(values)),key=lambda i:values[i])
    out=[0.0]*len(values); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]: j+=1
        r=0.5*(i+j-1)+1
        for k in range(i,j): out[order[k]]=r
        i=j
    return out

def weighted_jaccard(a:dict[str,float],b:dict[str,float]) -> float:
    keys=set(a)|set(b)
    den=sum(max(a.get(k,0.0),b.get(k,0.0)) for k in keys)
    return sum(min(a.get(k,0.0),b.get(k,0.0)) for k in keys)/den if den else 0.0

def country_residual(book:dict[str,dict[str,Any]]) -> dict[str,float]:
    net=defaultdict(float); activity=defaultdict(float)
    for r in book.values():
        c=r["country"]
        net[c]+=r["signed"]
        activity[c]+=r["activity"]
    out={}
    for k,r in book.items():
        c=r["country"]
        allocated=net[c]*(r["activity"]/activity[c]) if activity[c]>0 else 0.0
        out[k]=r["signed"]-allocated
    return out

def pair_metrics(a:dict[str,dict[str,Any]],b:dict[str,dict[str,Any]]) -> dict[str,float|int|None]:
    keys=sorted(set(a)|set(b))
    sa=[a.get(k,{}).get("signed",0.0) for k in keys]
    sb=[b.get(k,{}).get("signed",0.0) for k in keys]
    ra=country_residual(a); rb=country_residual(b)
    cra=[ra.get(k,0.0) for k in keys]; crb=[rb.get(k,0.0) for k in keys]
    la={k:r["w_long"] for k,r in a.items() if r["w_long"]>0}
    lb={k:r["w_long"] for k,r in b.items() if r["w_long"]>0}
    sha={k:r["w_short"] for k,r in a.items() if r["w_short"]>0}
    shb={k:r["w_short"] for k,r in b.items() if r["w_short"]>0}
    shared=set(a)&set(b)
    return {
        "union_count":len(keys),
        "shared_count":len(shared),
        "signed_pearson":pearson(sa,sb),
        "signed_spearman":pearson(ranks(sa),ranks(sb)),
        "country_neutral_pearson":pearson(cra,crb),
        "country_neutral_spearman":pearson(ranks(cra),ranks(crb)),
        "long_weighted_jaccard":weighted_jaccard(la,lb),
        "short_weighted_jaccard":weighted_jaccard(sha,shb),
        "long_support_jaccard":len(set(la)&set(lb))/len(set(la)|set(lb)) if set(la)|set(lb) else 0.0,
        "short_support_jaccard":len(set(sha)&set(shb))/len(set(sha)|set(shb)) if set(sha)|set(shb) else 0.0,
    }

def l1_country(a:dict[str,float],b:dict[str,float]) -> float:
    return sum(abs(a.get(k,0)-b.get(k,0)) for k in set(a)|set(b))

def p_upper(emp:float|None, vals:list[float]) -> float|None:
    if emp is None or not vals: return None
    return (1+sum(v>=emp for v in vals))/(1+len(vals))

def percentile(emp:float|None, vals:list[float]) -> float|None:
    if emp is None or not vals: return None
    return sum(v<=emp for v in vals)/len(vals)

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--outdir",default="qlbi_cross_manager")
    ap.add_argument("--max-candidates",type=int,default=60)
    ap.add_argument("--min-side",type=int,default=150)
    args=ap.parse_args()
    out=Path(args.outdir); out.mkdir(parents=True,exist_ok=True)
    con=duckdb.connect()
    try: con.execute("INSTALL httpfs")
    except Exception: pass
    con.execute("LOAD httpfs")

    con.execute(f"""
        CREATE TEMP TABLE target_meta AS
        SELECT s.ACCESSION_NUMBER, s.REPORT_DATE, s.FILING_DATE, s.SUB_TYPE,
               f.SERIES_NAME, f.SERIES_ID, f.TOTAL_ASSETS, f.NET_ASSETS,
               r.CIK, r.REGISTRANT_NAME
        FROM read_parquet('{SUBMISSION}', hive_partitioning=true) s
        JOIN read_parquet('{FUND_INFO}', hive_partitioning=true) f USING (ACCESSION_NUMBER)
        JOIN read_parquet('{REGISTRANT}', hive_partitioning=true) r USING (ACCESSION_NUMBER)
        WHERE s.REPORT_DATE=DATE '{REPORT_DATE}' AND s.SUB_TYPE='NPORT-P'
    """)
    con.execute(f"""
        CREATE TEMP TABLE broad_books AS
        SELECT h.ACCESSION_NUMBER,
               count(*) FILTER (WHERE upper(h.PAYOFF_PROFILE)='LONG') AS n_long,
               count(*) FILTER (WHERE upper(h.PAYOFF_PROFILE)='SHORT') AS n_short,
               sum(abs(h.CURRENCY_VALUE)) FILTER (WHERE upper(h.PAYOFF_PROFILE)='LONG') AS gross_long,
               sum(abs(h.CURRENCY_VALUE)) FILTER (WHERE upper(h.PAYOFF_PROFILE)='SHORT') AS gross_short,
               count(DISTINCT coalesce(h.INVESTMENT_COUNTRY,'__MISSING__')) AS n_countries
        FROM read_parquet('{HOLDINGS}', hive_partitioning=true) h
        SEMI JOIN target_meta m USING (ACCESSION_NUMBER)
        WHERE upper(h.ASSET_CAT)='EC' AND upper(h.PAYOFF_PROFILE) IN ('LONG','SHORT')
        GROUP BY h.ACCESSION_NUMBER
        HAVING n_long >= {args.min_side} AND n_short >= {args.min_side}
    """)
    rel=con.execute("""
        SELECT m.*, b.* EXCLUDE (ACCESSION_NUMBER)
        FROM target_meta m JOIN broad_books b USING (ACCESSION_NUMBER)
        ORDER BY m.ACCESSION_NUMBER
    """)
    cols=[d[0] for d in rel.description]
    summary=[dict(zip(cols,row)) for row in rel.fetchall()]
    by_acc={r['ACCESSION_NUMBER']:r for r in summary}
    if not AQR.issubset(by_acc):
        raise StudyError(f"AQR accessions absent from candidate universe: {AQR-set(by_acc)}")

    target_nlong=sum(fnum(by_acc[x]['n_long']) for x in AQR)/2
    target_nshort=sum(fnum(by_acc[x]['n_short']) for x in AQR)/2
    target_balance=sum(abs(math.log(fnum(by_acc[x]['gross_long'])/fnum(by_acc[x]['gross_short']))) for x in AQR)/2
    for r in summary:
        bal=abs(math.log(max(fnum(r['gross_long']),1)/max(fnum(r['gross_short']),1)))
        r['pre_distance']=(abs(math.log(fnum(r['n_long'])/target_nlong))+
                           abs(math.log(fnum(r['n_short'])/target_nshort))+
                           abs(bal-target_balance))
    pre=sorted(summary,key=lambda r:r['pre_distance'])[:max(args.max_candidates*3,100)]
    pre_acc={r['ACCESSION_NUMBER'] for r in pre}|AQR
    quoted_pre=','.join("'"+x+"'" for x in sorted(pre_acc))
    hrel=con.execute(f"""
        SELECT ACCESSION_NUMBER,HOLDING_ID,ISSUER_NAME,ISSUER_TITLE,ISSUER_CUSIP,
               INVESTMENT_COUNTRY,PAYOFF_PROFILE,abs(CURRENCY_VALUE) AS value_usd
        FROM read_parquet('{HOLDINGS}', hive_partitioning=true)
        WHERE ACCESSION_NUMBER IN ({quoted_pre}) AND upper(ASSET_CAT)='EC'
          AND upper(PAYOFF_PROFILE) IN ('LONG','SHORT')
        ORDER BY ACCESSION_NUMBER,HOLDING_ID
    """)
    holding_rows=hrel.fetchall()
    cprof=defaultdict(dict); ctot=defaultdict(float); country_gross=defaultdict(lambda:defaultdict(float))
    for acc,hid,name,title,cusip,country,side,value in holding_rows:
        c=text(country) or '__MISSING__'
        country_gross[acc][c]+=fnum(value); ctot[acc]+=fnum(value)
    for acc,profile in country_gross.items():
        if ctot[acc]>0: cprof[acc]={c:v/ctot[acc] for c,v in profile.items()}
    target_country={}
    for c in set(cprof[AQR_A])|set(cprof[AQR_B]):
        target_country[c]=0.5*(cprof[AQR_A].get(c,0)+cprof[AQR_B].get(c,0))
    for r in pre:
        r['country_l1_to_aqr']=l1_country(cprof.get(r['ACCESSION_NUMBER'],{}),target_country)
        r['match_distance']=r['pre_distance']+2*r['country_l1_to_aqr']
    selected=sorted(pre,key=lambda r:r['match_distance'])[:args.max_candidates]
    selected_acc={r['ACCESSION_NUMBER'] for r in selected}|AQR
    books_raw=defaultdict(lambda:defaultdict(lambda:{"long":0.0,"short":0.0,"country":"XX","name":""}))
    for acc,hid,name,title,cusip,country,side,value in holding_rows:
        if acc not in selected_acc: continue
        k=security_key(cusip,country,name,title)
        rec=books_raw[acc][k]
        rec['country']=text(country) or 'XX'; rec['name']=text(name) or text(title) or k
        rec['long' if str(side).upper()=='LONG' else 'short']+=fnum(value)
    books={}
    for acc,raw in books_raw.items():
        gl=sum(r['long'] for r in raw.values()); gs=sum(r['short'] for r in raw.values())
        if gl<=0 or gs<=0: continue
        book={}
        for k,r in raw.items():
            wl=r['long']/gl; ws=r['short']/gs
            book[k]={**r,"w_long":wl,"w_short":ws,"signed":wl-ws,"activity":0.5*(wl+ws)}
        books[acc]=book
    if not AQR.issubset(books): raise StudyError("AQR books absent after extraction")

    empirical=pair_metrics(books[AQR_A],books[AQR_B])
    selected_meta={r['ACCESSION_NUMBER']:r for r in selected if r['ACCESSION_NUMBER'] in books}
    null_rows=[]
    accs=sorted(selected_meta)
    for i,a in enumerate(accs):
        for b in accs[i+1:]:
            ma,mb=selected_meta[a],selected_meta[b]
            if ma['CIK']==mb['CIK'] or ma['REGISTRANT_NAME']==mb['REGISTRANT_NAME']: continue
            count_ratio=max(fnum(ma['n_long'])/max(fnum(mb['n_long']),1),fnum(mb['n_long'])/max(fnum(ma['n_long']),1),
                            fnum(ma['n_short'])/max(fnum(mb['n_short']),1),fnum(mb['n_short'])/max(fnum(ma['n_short']),1))
            country_gap=l1_country(cprof.get(a,{}),cprof.get(b,{}))
            if count_ratio>2.0 or country_gap>0.65: continue
            m=pair_metrics(books[a],books[b])
            null_rows.append({"accession_a":a,"accession_b":b,"registrant_a":ma['REGISTRANT_NAME'],"registrant_b":mb['REGISTRANT_NAME'],
                              "series_a":ma['SERIES_NAME'],"series_b":mb['SERIES_NAME'],"country_l1":country_gap,"count_ratio":count_ratio,**m})
    if len(null_rows)<20:
        raise StudyError(f"Too few matched unrelated pairs: {len(null_rows)}")

    metric_names=["signed_pearson","signed_spearman","country_neutral_pearson","country_neutral_spearman",
          "long_weighted_jaccard","short_weighted_jaccard","long_support_jaccard","short_support_jaccard"]
    null={k:[fnum(r[k]) for r in null_rows if r[k] is not None] for k in metric_names}
    comparison={k:{"empirical":empirical[k],"p_upper":p_upper(empirical[k],null[k]),"percentile":percentile(empirical[k],null[k]),
                   "null_n":len(null[k]),"null_median":sorted(null[k])[len(null[k])//2],"null_max":max(null[k])} for k in metric_names}
    aqr_unrelated=[]
    for target in (AQR_A,AQR_B):
        for acc,meta in selected_meta.items():
            if acc in AQR or meta['CIK']==by_acc[target]['CIK']: continue
            m=pair_metrics(books[target],books[acc])
            aqr_unrelated.append({"aqr_accession":target,"other_accession":acc,"other_registrant":meta['REGISTRANT_NAME'],"other_series":meta['SERIES_NAME'],**m})

    def write_csv(path:Path,rows:list[dict[str,Any]]):
        if not rows: return
        fields=[]
        for r in rows:
            for k in r:
                if k not in fields: fields.append(k)
        with path.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    clean_summary=[]
    for r in selected:
        clean_summary.append({k:(str(v) if hasattr(v,'as_tuple') else v) for k,v in r.items()})
    write_csv(out/'candidate_funds.csv',clean_summary)
    write_csv(out/'matched_unrelated_pairs.csv',sorted(null_rows,key=lambda r:fnum(r['signed_pearson']),reverse=True))
    write_csv(out/'aqr_vs_unrelated.csv',sorted(aqr_unrelated,key=lambda r:fnum(r['signed_pearson']),reverse=True))
    result={
        "status":"EXECUTED",
        "source_authority":"U.S. SEC Form N-PORT quarterly structured data",
        "transport":"trader298/sec-nport typed Parquet mirror",
        "report_date":REPORT_DATE,
        "candidate_fund_count":len(selected_meta),
        "matched_unrelated_pair_count":len(null_rows),
        "aqr_sibling":empirical,
        "cross_manager_null":comparison,
        "discipline":{"direct_short_is_exposure_not_intent":True,"distinct_registrant_is_not_a_complete_parent_adviser_bridge":True},
        "gate":"CROSS_MANAGER_RAW_AND_COUNTRY_NEUTRAL_PASS" if comparison['country_neutral_pearson']['p_upper'] is not None and comparison['country_neutral_pearson']['p_upper']<=0.01 else "CROSS_MANAGER_GATE_FAIL_OR_INCONCLUSIVE",
    }
    (out/'metrics.json').write_text(json.dumps(result,indent=2,ensure_ascii=False,default=str)+'\n',encoding='utf-8')
    lines=["# QLBI same-date cross-manager null","",f"Gate: `{result['gate']}`","",f"Candidate funds: {len(selected_meta)}; matched unrelated pairs: {len(null_rows)}.","","| Metric | AQR sibling | Null median | Null max | Upper-tail p | Percentile |","|---|---:|---:|---:|---:|---:|"]
    for k in metric_names:
        c=comparison[k]; lines.append(f"| {k} | {c['empirical']:.6f} | {c['null_median']:.6f} | {c['null_max']:.6f} | {c['p_upper']:.6g} | {c['percentile']:.4f} |")
    lines += ["","Direct short exposure is not labelled as negative-alpha intent. Distinct registrant is an interim, not complete, adviser-identity control."]
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False,default=str))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
