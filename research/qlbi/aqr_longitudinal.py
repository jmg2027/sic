#!/usr/bin/env python3
"""Longitudinal AQR sibling-stock-engine validation from public N-PORT data.

For every report date where both target AQR series filed a public NPORT-P, the
program reconstructs direct cash-equity long/short books, measures same-date
coherence, and measures whether quarter-to-quarter signed position changes are
also shared. The time series is a stronger test than one cross-section because
a common static universe alone should not explain synchronized rebalancing.

No direct short is labelled as negative-alpha intent. U.S.-cash-equity masks
are synthetic 13F proxies, not Official 13(f) List membership tests.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

DATASET="trader298/sec-nport"
BASE=f"hf://datasets/{DATASET}"
SERIES_A="S000046740"
SERIES_B="S000041116"
SERIES={SERIES_A:"AQR Equity Market Neutral Fund",SERIES_B:"AQR Long-Short Equity Fund"}
NULLS={"","N/A","NA","NONE","NULL","NOT AVAILABLE"}

class StudyError(RuntimeError): pass

def clean(v:Any)->str|None:
    if v is None:return None
    x=str(v).strip()
    return None if x.upper() in NULLS else x

def fnum(v:Any)->float:
    try:x=float(v)
    except (TypeError,ValueError):return 0.0
    return x if math.isfinite(x) else 0.0

def norm_id(v:Any)->str|None:
    x=clean(v)
    if x is None:return None
    y=re.sub(r"[^A-Za-z0-9]","",x).upper()
    return y or None

def norm_name(v:Any)->str:
    x=re.sub(r"[^A-Za-z0-9]+"," ",(clean(v) or "").upper()).strip()
    suffix={"INC","INCORPORATED","CORP","CORPORATION","CO","COMPANY","LTD","LIMITED","PLC","SA","NV","AG","SE","LLC","LP"}
    return " ".join(t for t in x.split() if t not in suffix)

def security_key(cusip:Any,country:Any,name:Any,title:Any)->str:
    c=norm_id(cusip)
    if c and 6<=len(c)<=12:return "CUSIP:"+c
    cc=norm_id(country) or "XX"; n=norm_name(name or title)
    if not n:raise StudyError("holding has no usable security key")
    return f"NAME:{cc}:{n}:{norm_name(title)[:24]}"

def pearson_dict(a:dict[str,float],b:dict[str,float])->float|None:
    keys=sorted(set(a)|set(b))
    if len(keys)<3:return None
    x=np.array([a.get(k,0.0) for k in keys],float)
    y=np.array([b.get(k,0.0) for k in keys],float)
    if np.std(x)<=0 or np.std(y)<=0:return None
    return float(np.corrcoef(x,y)[0,1])

def rankdata(x:np.ndarray)->np.ndarray:
    return pd.Series(x).rank(method="average").to_numpy(float)

def spearman_dict(a:dict[str,float],b:dict[str,float])->float|None:
    keys=sorted(set(a)|set(b))
    if len(keys)<3:return None
    x=np.array([a.get(k,0.0) for k in keys],float);y=np.array([b.get(k,0.0) for k in keys],float)
    if np.std(x)<=0 or np.std(y)<=0:return None
    return float(np.corrcoef(rankdata(x),rankdata(y))[0,1])

def weighted_jaccard(a:dict[str,float],b:dict[str,float])->float:
    keys=set(a)|set(b); den=sum(max(a.get(k,0),b.get(k,0)) for k in keys)
    return sum(min(a.get(k,0),b.get(k,0)) for k in keys)/den if den else 0.0

def common_mass(a:dict[str,float],b:dict[str,float])->float:
    return sum(min(a.get(k,0),b.get(k,0)) for k in set(a)|set(b))

def support_jaccard(a:dict[str,float],b:dict[str,float])->float:
    aa={k for k,v in a.items() if v>0};bb={k for k,v in b.items() if v>0}
    return len(aa&bb)/len(aa|bb) if aa|bb else 0.0

def energy_common(a:dict[str,float],b:dict[str,float])->float:
    keys=set(a)|set(b)
    x=np.array([a.get(k,0) for k in keys]);y=np.array([b.get(k,0) for k in keys])
    den=0.5*(np.sum(x*x)+np.sum(y*y))
    return float(np.sum((0.5*(x+y))**2)/den) if den>0 else 0.0

def country_residual(book:dict[str,dict[str,Any]])->dict[str,float]:
    net=defaultdict(float);activity=defaultdict(float)
    for r in book.values():
        c=r['country'];net[c]+=r['signed'];activity[c]+=r['activity']
    return {k:r['signed']-net[r['country']]*(r['activity']/activity[r['country']]) if activity[r['country']]>0 else r['signed'] for k,r in book.items()}

def book_metrics(a:dict[str,dict[str,Any]],b:dict[str,dict[str,Any]])->dict[str,Any]:
    sa={k:r['signed'] for k,r in a.items()};sb={k:r['signed'] for k,r in b.items()}
    la={k:r['w_long'] for k,r in a.items() if r['w_long']>0};lb={k:r['w_long'] for k,r in b.items() if r['w_long']>0}
    sha={k:r['w_short'] for k,r in a.items() if r['w_short']>0};shb={k:r['w_short'] for k,r in b.items() if r['w_short']>0}
    ca=country_residual(a);cb=country_residual(b)
    shared=set(a)&set(b)
    opposite=sum(1 for k in shared if sa[k]*sb[k]<0)
    activity_same=sum(min(a[k]['activity'],b[k]['activity']) for k in shared if sa[k]*sb[k]>=0)
    activity_all=sum(min(a[k]['activity'],b[k]['activity']) for k in shared)
    return {
        'union_count':len(set(a)|set(b)),'shared_count':len(shared),
        'signed_pearson':pearson_dict(sa,sb),'signed_spearman':spearman_dict(sa,sb),
        'country_neutral_pearson':pearson_dict(ca,cb),'country_neutral_spearman':spearman_dict(ca,cb),
        'long_weighted_jaccard':weighted_jaccard(la,lb),'short_weighted_jaccard':weighted_jaccard(sha,shb),
        'long_support_jaccard':support_jaccard(la,lb),'short_support_jaccard':support_jaccard(sha,shb),
        'long_common_mass':common_mass(la,lb),'short_common_mass':common_mass(sha,shb),
        'common_energy_share':energy_common(sa,sb),'opposite_side_rate':opposite/len(shared) if shared else None,
        'weighted_same_side_rate':activity_same/activity_all if activity_all else None,
    }

def synthetic_13f(book:dict[str,dict[str,Any]])->dict[str,float]:
    visible={k:r['w_long'] for k,r in book.items() if r['country']=='US' and k.startswith('CUSIP:') and r['w_long']>0}
    total=sum(visible.values())
    return {k:v/total for k,v in visible.items()} if total>0 else {}

def all_partition_uris(table:str)->list[str]:
    out=[]
    for year in range(2019,2027):
        quarters=range(1,5)
        if year==2019:quarters=[4]
        if year==2026:quarters=[1,2]
        for q in quarters:out.append(f"{BASE}/{table}/year={year}/quarter={q}/data.parquet")
    return out

def sql_list(values:list[str])->str:
    return '['+','.join("'"+v.replace("'","''")+"'" for v in values)+']'

def load_metadata(con:duckdb.DuckDBPyConnection)->pd.DataFrame:
    fi=sql_list(all_partition_uris('FUND_REPORTED_INFO'));sub=sql_list(all_partition_uris('SUBMISSION'))
    query=f"""
    WITH f AS (
      SELECT ACCESSION_NUMBER,SERIES_NAME,SERIES_ID,year,quarter
      FROM read_parquet({fi},hive_partitioning=true,union_by_name=true)
      WHERE SERIES_ID IN ('{SERIES_A}','{SERIES_B}')
    ), s AS (
      SELECT ACCESSION_NUMBER,FILING_DATE,REPORT_DATE,REPORT_ENDING_PERIOD,SUB_TYPE,IS_LAST_FILING,year,quarter
      FROM read_parquet({sub},hive_partitioning=true,union_by_name=true)
      WHERE SUB_TYPE='NPORT-P'
    )
    SELECT f.*,s.FILING_DATE,s.REPORT_DATE,s.REPORT_ENDING_PERIOD,s.IS_LAST_FILING
    FROM f JOIN s USING(ACCESSION_NUMBER,year,quarter)
    ORDER BY REPORT_DATE,SERIES_ID,FILING_DATE,ACCESSION_NUMBER
    """
    df=con.execute(query).fetchdf()
    if df.empty:raise StudyError('No target series metadata found')
    df['REPORT_DATE']=pd.to_datetime(df['REPORT_DATE']);df['FILING_DATE']=pd.to_datetime(df['FILING_DATE'])
    df=df.sort_values(['REPORT_DATE','SERIES_ID','FILING_DATE','ACCESSION_NUMBER']).drop_duplicates(['REPORT_DATE','SERIES_ID'],keep='first')
    counts=df.groupby('REPORT_DATE')['SERIES_ID'].nunique()
    dates=set(counts[counts==2].index)
    return df[df['REPORT_DATE'].isin(dates)].copy()

def load_holdings_for_partition(con:duckdb.DuckDBPyConnection,year:int,quarter:int,accessions:list[str])->pd.DataFrame:
    uri=f"{BASE}/FUND_REPORTED_HOLDING/year={year}/quarter={quarter}/data.parquet"
    quoted=','.join("'"+a+"'" for a in accessions)
    query=f"""
    SELECT ACCESSION_NUMBER,HOLDING_ID,ISSUER_NAME,ISSUER_TITLE,ISSUER_CUSIP,
           INVESTMENT_COUNTRY,PAYOFF_PROFILE,abs(CURRENCY_VALUE) AS value_usd
    FROM read_parquet('{uri}',hive_partitioning=true)
    WHERE ACCESSION_NUMBER IN ({quoted}) AND upper(ASSET_CAT)='EC'
      AND upper(PAYOFF_PROFILE) IN ('LONG','SHORT')
    """
    return con.execute(query).fetchdf()

def build_book(rows:pd.DataFrame,accession:str)->tuple[dict[str,dict[str,Any]],dict[str,Any]]:
    raw=defaultdict(lambda:{'long':0.0,'short':0.0,'country':'XX','name':''})
    for r in rows[rows['ACCESSION_NUMBER']==accession].itertuples(index=False):
        k=security_key(r.ISSUER_CUSIP,r.INVESTMENT_COUNTRY,r.ISSUER_NAME,r.ISSUER_TITLE)
        rec=raw[k];rec['country']=clean(r.INVESTMENT_COUNTRY) or 'XX';rec['name']=clean(r.ISSUER_NAME) or clean(r.ISSUER_TITLE) or k
        rec['long' if str(r.PAYOFF_PROFILE).upper()=='LONG' else 'short']+=fnum(r.value_usd)
    gl=sum(r['long'] for r in raw.values());gs=sum(r['short'] for r in raw.values())
    if gl<=0 or gs<=0:raise StudyError(f'accession {accession} lacks both cash-equity sides')
    book={}
    for k,r in raw.items():
        wl=r['long']/gl;ws=r['short']/gs
        book[k]={**r,'w_long':wl,'w_short':ws,'signed':wl-ws,'activity':0.5*(wl+ws)}
    return book,{'gross_long_usd':gl,'gross_short_usd':gs,'unique_securities':len(book),'long_count':sum(r['long']>0 for r in raw.values()),'short_count':sum(r['short']>0 for r in raw.values())}

def delta_vector(current:dict[str,dict[str,Any]],previous:dict[str,dict[str,Any]])->dict[str,float]:
    return {k:current.get(k,{}).get('signed',0.0)-previous.get(k,{}).get('signed',0.0) for k in set(current)|set(previous)}

def delta_direction_agreement(a:dict[str,float],b:dict[str,float])->float|None:
    keys=set(a)|set(b);weights=[];agree=[]
    for k in keys:
        x=a.get(k,0);y=b.get(k,0);w=min(abs(x),abs(y))
        if w<=0:continue
        weights.append(w);agree.append(1.0 if x*y>=0 else 0.0)
    return float(np.average(agree,weights=weights)) if weights else None

def summarize(values:list[float|None])->dict[str,float|int|None]:
    arr=np.array([v for v in values if v is not None and np.isfinite(v)],float)
    if len(arr)==0:return {'n':0,'median':None,'min':None,'p10':None,'p90':None,'max':None}
    return {'n':int(len(arr)),'median':float(np.median(arr)),'min':float(np.min(arr)),'p10':float(np.quantile(arr,.1)),'p90':float(np.quantile(arr,.9)),'max':float(np.max(arr))}

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''):h.update(block)
    return h.hexdigest()

def main()->int:
    ap=argparse.ArgumentParser();ap.add_argument('--outdir',default='qlbi_aqr_longitudinal');args=ap.parse_args()
    out=Path(args.outdir);out.mkdir(parents=True,exist_ok=True)
    con=duckdb.connect()
    try:con.execute('INSTALL httpfs')
    except Exception:pass
    con.execute('LOAD httpfs')
    meta=load_metadata(con)
    records=[];books_by_date={};diag_by_date={}
    for date,group in meta.groupby('REPORT_DATE'):
        accessions=dict(zip(group['SERIES_ID'],group['ACCESSION_NUMBER']))
        frames=[]
        for (year,quarter),part in group.groupby(['year','quarter']):
            frames.append(load_holdings_for_partition(con,int(year),int(quarter),part['ACCESSION_NUMBER'].tolist()))
        rows=pd.concat(frames,ignore_index=True)
        a,da=build_book(rows,accessions[SERIES_A]);b,db=build_book(rows,accessions[SERIES_B])
        metrics=book_metrics(a,b);va=synthetic_13f(a);vb=synthetic_13f(b)
        metrics.update({
            'report_date':str(pd.Timestamp(date).date()),'filing_date_a':str(group[group.SERIES_ID==SERIES_A].iloc[0].FILING_DATE.date()),
            'filing_date_b':str(group[group.SERIES_ID==SERIES_B].iloc[0].FILING_DATE.date()),
            'accession_a':accessions[SERIES_A],'accession_b':accessions[SERIES_B],
            'gross_long_scale_b_over_a':db['gross_long_usd']/da['gross_long_usd'],
            'gross_short_scale_b_over_a':db['gross_short_usd']/da['gross_short_usd'],
            'visible_long_mass_a':sum(r['w_long'] for k,r in a.items() if r['country']=='US' and k.startswith('CUSIP:')),
            'visible_long_mass_b':sum(r['w_long'] for k,r in b.items() if r['country']=='US' and k.startswith('CUSIP:')),
            'synthetic_13f_sibling_pearson':pearson_dict(va,vb),'synthetic_13f_sibling_spearman':spearman_dict(va,vb),
            'synthetic_13f_weighted_jaccard':weighted_jaccard(va,vb),
            'unique_a':da['unique_securities'],'unique_b':db['unique_securities'],
        })
        records.append(metrics);books_by_date[pd.Timestamp(date)]=(a,b);diag_by_date[pd.Timestamp(date)]=(da,db)
    if len(records)<4:raise StudyError(f'Too few paired dates: {len(records)}')
    records=sorted(records,key=lambda r:r['report_date'])
    for i in range(1,len(records)):
        d0=pd.Timestamp(records[i-1]['report_date']);d1=pd.Timestamp(records[i]['report_date'])
        a0,b0=books_by_date[d0];a1,b1=books_by_date[d1]
        da=delta_vector(a1,a0);db=delta_vector(b1,b0)
        records[i]['delta_signed_pearson']=pearson_dict(da,db)
        records[i]['delta_signed_spearman']=spearman_dict(da,db)
        records[i]['delta_weighted_direction_agreement']=delta_direction_agreement(da,db)
        common0={k:0.5*(a0.get(k,{}).get('signed',0)+b0.get(k,{}).get('signed',0)) for k in set(a0)|set(b0)}
        common1={k:0.5*(a1.get(k,{}).get('signed',0)+b1.get(k,{}).get('signed',0)) for k in set(a1)|set(b1)}
        records[i]['common_engine_inventory_persistence']=pearson_dict(common0,common1)
    records[0]['delta_signed_pearson']=None;records[0]['delta_signed_spearman']=None;records[0]['delta_weighted_direction_agreement']=None;records[0]['common_engine_inventory_persistence']=None
    frame=pd.DataFrame(records);frame.to_csv(out/'quarterly_metrics.csv',index=False,quoting=csv.QUOTE_MINIMAL)
    keys=['signed_pearson','signed_spearman','country_neutral_pearson','long_weighted_jaccard','short_weighted_jaccard','long_common_mass','short_common_mass','common_energy_share','weighted_same_side_rate','synthetic_13f_sibling_pearson','synthetic_13f_weighted_jaccard','delta_signed_pearson','delta_signed_spearman','delta_weighted_direction_agreement','common_engine_inventory_persistence']
    summary={k:summarize(frame[k].tolist()) for k in keys}
    pass_dates=int((frame['signed_pearson']>=0.8).sum());delta_pass=int((frame['delta_signed_pearson'].fillna(-1)>=0.5).sum())
    gate='LONGITUDINAL_COMMON_ENGINE_PASS' if len(frame)>=8 and pass_dates/len(frame)>=0.8 and summary['delta_signed_pearson']['median'] is not None and summary['delta_signed_pearson']['median']>=0.5 else 'LONGITUDINAL_GATE_FAIL_OR_INCONCLUSIVE'
    result={'status':'EXECUTED','gate':gate,'paired_report_dates':len(frame),'first_report_date':frame.report_date.min(),'last_report_date':frame.report_date.max(),'dates_signed_corr_ge_0_8':pass_dates,'change_dates_delta_corr_ge_0_5':delta_pass,'summary':summary,'provenance':{'authority':'U.S. SEC Form N-PORT quarterly structured data','transport':DATASET+' typed Parquet mirror','direct_short_is_exposure_not_intent':True,'synthetic_13f_is_us_cash_cusip_proxy_not_official_list':True},'limitations':['Series identity is fixed to the two AQR registered funds; this does not prove every AQR vehicle uses the same engine.','Derivative overlays are excluded from direct cash-equity comparisons.','This is structural validation, not an OOS return-prediction test.']}
    (out/'metrics.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    meta.to_csv(out/'filing_metadata.csv',index=False)
    lines=['# QLBI AQR longitudinal sibling-engine validation','',f"Gate: `{gate}`",'',f"Paired dates: {len(frame)} ({frame.report_date.min()} to {frame.report_date.max()}).",'','| Metric | N | Median | P10 | Min | Max |','|---|---:|---:|---:|---:|---:|']
    for k in keys:
        s=summary[k];lines.append(f"| {k} | {s['n']} | {s['median']} | {s['p10']} | {s['min']} | {s['max']} |")
    lines += ['','Observed shorts are economic exposures, not automatically bearish intent. The synthetic 13F mask is a proxy, not Official 13(f) List membership.']
    (out/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps({'script_sha256':sha256(Path(__file__)),'outputs':sorted(p.name for p in out.iterdir())},indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2,ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
