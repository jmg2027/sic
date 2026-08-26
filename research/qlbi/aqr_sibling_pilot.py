#!/usr/bin/env python3
"""Direct cash-equity stock-book comparison for two AQR N-PORT filings.

Research-only. Reported shorts are exposures, not automatically alpha views.
The output gate remains pending factor-neutral and cross-manager validation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def lname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def clean(x):
    if x is None:
        return None
    x = str(x).strip()
    return None if x.upper() in {"", "N/A", "NA", "NONE", "NULL"} else x


def number(x):
    x = clean(x)
    try:
        y = float(x.replace(",", "")) if x is not None else None
        return y if y is not None and math.isfinite(y) else None
    except ValueError:
        return None


def direct(node, name):
    for c in list(node):
        if lname(c.tag) == name:
            return c
    return None


def text(node, name):
    c = direct(node, name)
    return clean(c.text) if c is not None else None


def desc(root, name):
    for e in root.iter():
        if lname(e.tag) == name:
            return e
    return None


def attr(node, name):
    if node is None:
        return None
    for k, v in node.attrib.items():
        if lname(k) == name:
            return clean(v)
    return None


def ident(inv, name):
    ids = direct(inv, "identifiers")
    item = direct(ids, name) if ids is not None else None
    return attr(item, "value") or (clean(item.text) if item is not None else None)


def norm_id(x):
    x = clean(x)
    return re.sub(r"[^A-Za-z0-9]", "", x).upper() if x else None


def norm_name(x):
    x = re.sub(r"[^A-Za-z0-9]+", " ", (x or "").upper()).strip()
    suffix = {"INC", "INCORPORATED", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC", "SA", "NV", "AG", "SE", "LLC"}
    return " ".join(p for p in x.split() if p not in suffix)


def key_for(cusip, isin, ticker, country, name, title):
    c, i, t = norm_id(cusip), norm_id(isin), norm_id(ticker)
    if c and len(c) >= 6:
        return "CUSIP:" + c, "CUSIP"
    if i and len(i) >= 10:
        return "ISIN:" + i, "ISIN"
    n = norm_name(name or title)
    cc = norm_id(country) or "XX"
    if t:
        return f"TICKER:{cc}:{t}:{n[:24]}", "TICKER_NAME"
    if n:
        return f"NAME:{cc}:{n}:{norm_name(title)[:24]}", "NAME"
    raise ValueError("holding has no usable identifier")


def code(inv, plain, conditional, attribute):
    x = text(inv, plain)
    return x if x is not None else attr(direct(inv, conditional), attribute)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse(path):
    root = ET.parse(path).getroot()
    gen, fund = desc(root, "genInfo"), desc(root, "fundInfo")
    meta = {
        "path": str(path), "sha256": sha256(path),
        "registrant": text(gen, "regName") if gen is not None else None,
        "series_name": text(gen, "seriesName") if gen is not None else None,
        "series_id": text(gen, "seriesId") if gen is not None else None,
        "report_date": (text(gen, "repPdDate") or text(gen, "repPdEnd")) if gen is not None else None,
        "total_assets": number(text(fund, "totAssets")) if fund is not None else None,
        "net_assets": number(text(fund, "netAssets")) if fund is not None else None,
    }
    rows = []
    for inv in root.iter():
        if lname(inv.tag) != "invstOrSec":
            continue
        name, title = text(inv, "name"), text(inv, "title")
        cusip, isin, ticker = norm_id(text(inv, "cusip")), norm_id(ident(inv, "isin")), ident(inv, "ticker")
        country = text(inv, "invCountry") or text(inv, "invOthCountry")
        asset = code(inv, "assetCat", "assetConditional", "assetCat")
        issuer = code(inv, "issuerCat", "issuerConditional", "issuerCat")
        payoff = (text(inv, "payoffProfile") or "").upper()
        derivative = direct(inv, "derivativeInfo") is not None
        k, source = key_for(cusip, isin, ticker, country, name, title)
        raw_value = number(text(inv, "valUSD"))
        rows.append({
            "key": k, "key_source": source, "name": name, "title": title,
            "cusip": cusip, "isin": isin, "ticker": ticker, "country": country,
            "asset": asset, "issuer": issuer, "payoff": payoff,
            "value": abs(raw_value) if raw_value is not None else None,
            "balance": number(text(inv, "balance")), "units": text(inv, "units"),
            "derivative": derivative,
        })
    if not rows:
        raise RuntimeError("no invstOrSec records")
    return meta, rows


def make_book(rows):
    cash = [r for r in rows if not r["derivative"] and (r["asset"] or "").upper() == "EC"]
    side_cov = sum(r["payoff"] in {"LONG", "SHORT"} for r in cash) / len(cash)
    value_cov = sum(r["value"] is not None for r in cash) / len(cash)
    if side_cov < 0.98 or value_cov < 0.98:
        raise RuntimeError(f"coverage failure side={side_cov:.4f} value={value_cov:.4f}")
    out = {}
    for r in cash:
        if r["payoff"] not in {"LONG", "SHORT"} or r["value"] is None:
            continue
        x = out.setdefault(r["key"], {
            "key": r["key"], "name": r["name"], "title": r["title"],
            "cusip": r["cusip"], "isin": r["isin"], "ticker": r["ticker"], "country": r["country"],
            "long_value": 0.0, "short_value": 0.0,
        })
        x[r["payoff"].lower() + "_value"] += r["value"]
    gl = sum(x["long_value"] for x in out.values())
    gs = sum(x["short_value"] for x in out.values())
    if gl <= 0 or gs <= 0:
        raise RuntimeError(f"both sides required: long={gl} short={gs}")
    for x in out.values():
        x["w_long"] = x["long_value"] / gl
        x["w_short"] = x["short_value"] / gs
        x["signed"] = x["w_long"] - x["w_short"]
        x["activity"] = 0.5 * (x["w_long"] + x["w_short"])
    diag = {
        "cash_rows": len(cash), "unique_securities": len(out),
        "side_coverage": side_cov, "value_coverage": value_cov,
        "gross_long_usd": gl, "gross_short_usd": gs, "net_usd": gl-gs,
        "long_count": sum(x["long_value"] > 0 for x in out.values()),
        "short_count": sum(x["short_value"] > 0 for x in out.values()),
    }
    return out, diag


def align(a, b):
    rows = []
    for k in sorted(set(a) | set(b)):
        aa, bb = a.get(k, {}), b.get(k, {})
        r = {"key": k}
        for f in ("name", "title", "cusip", "isin", "ticker", "country"):
            r[f] = aa.get(f) or bb.get(f)
        for s, x in (("a", aa), ("b", bb)):
            for f in ("long_value", "short_value", "w_long", "w_short", "signed", "activity"):
                r[f + "_" + s] = float(x.get(f, 0.0))
        r["common_long"] = min(r["w_long_a"], r["w_long_b"])
        r["common_short"] = min(r["w_short_a"], r["w_short_b"])
        r["common_signed"] = 0.5 * (r["signed_a"] + r["signed_b"])
        r["signed_spread"] = r["signed_a"] - r["signed_b"]
        r["shared"] = r["activity_a"] > 0 and r["activity_b"] > 0
        r["opposite"] = r["signed_a"] * r["signed_b"] < 0
        r["same_side"] = r["shared"] and not r["opposite"] and r["signed_a"] != 0 and r["signed_b"] != 0
        rows.append(r)
    return rows


def pearson(a, b):
    if len(a) < 3:
        return None
    ma, mb = sum(a)/len(a), sum(b)/len(b)
    va, vb = sum((x-ma)**2 for x in a), sum((x-mb)**2 for x in b)
    return sum((x-ma)*(y-mb) for x, y in zip(a, b))/math.sqrt(va*vb) if va > 0 and vb > 0 else None


def rank(x):
    order = sorted(range(len(x)), key=x.__getitem__)
    out = [0.0]*len(x)
    i = 0
    while i < len(order):
        j = i+1
        while j < len(order) and x[order[j]] == x[order[i]]:
            j += 1
        v = 0.5*(i+j-1)+1
        for p in order[i:j]: out[p] = v
        i = j
    return out


def cosine(a, b):
    d = math.sqrt(sum(x*x for x in a)*sum(y*y for y in b))
    return sum(x*y for x, y in zip(a,b))/d if d else None


def wj(a, b):
    d = sum(max(x,y) for x,y in zip(a,b))
    return sum(min(x,y) for x,y in zip(a,b))/d if d else None


def sj(a, b):
    aa, bb = {i for i,x in enumerate(a) if x>0}, {i for i,x in enumerate(b) if x>0}
    return len(aa&bb)/len(aa|bb) if aa|bb else None


def top_set(rows, col, frac=0.10):
    x = [r for r in rows if r[col] > 0]
    n = max(1, math.ceil(frac*len(x))) if x else 0
    return {r["key"] for r in sorted(x, key=lambda r:r[col], reverse=True)[:n]}


def metrics(rows):
    sa, sb = [r["signed_a"] for r in rows], [r["signed_b"] for r in rows]
    la, lb = [r["w_long_a"] for r in rows], [r["w_long_b"] for r in rows]
    xa, xb = [r["w_short_a"] for r in rows], [r["w_short_b"] for r in rows]
    shared = [r for r in rows if r["shared"]]
    weights = [min(r["activity_a"],r["activity_b"]) for r in shared]
    out = {
        "union_count": len(rows), "shared_active_count": len(shared),
        "signed_pearson": pearson(sa,sb), "signed_spearman": pearson(rank(sa),rank(sb)),
        "signed_cosine": cosine(sa,sb),
        "long_weighted_jaccard": wj(la,lb), "short_weighted_jaccard": wj(xa,xb),
        "long_support_jaccard": sj(la,lb), "short_support_jaccard": sj(xa,xb),
        "long_common_mass": sum(min(x,y) for x,y in zip(la,lb)),
        "short_common_mass": sum(min(x,y) for x,y in zip(xa,xb)),
        "half_l1_signed_distance": 0.5*sum(abs(x-y) for x,y in zip(sa,sb)),
        "opposite_side_count": sum(r["opposite"] for r in rows),
        "opposite_side_rate_shared": sum(r["opposite"] for r in shared)/len(shared) if shared else None,
        "weighted_same_side_rate": sum(w*r["same_side"] for w,r in zip(weights,shared))/sum(weights) if sum(weights)>0 else None,
    }
    for side in ("long","short"):
        a,b=top_set(rows,f"w_{side}_a"),top_set(rows,f"w_{side}_b")
        out[f"top10_{side}_a"] = len(a); out[f"top10_{side}_b"] = len(b)
        out[f"top10_{side}_intersection"] = len(a&b)
        out[f"top10_{side}_jaccard"] = len(a&b)/len(a|b) if a|b else None
        out[f"top10_{side}_overlap_coefficient"] = len(a&b)/min(len(a),len(b)) if a and b else None
    return out


def quantile(x,q):
    if not x: return None
    x=sorted(x); p=(len(x)-1)*q; lo=math.floor(p); hi=math.ceil(p)
    return x[lo] if lo==hi else x[lo]*(hi-p)+x[hi]*(p-lo)


def permute(rows, n, seed, by_country=True):
    rng=random.Random(seed); observed=metrics(rows); groups=defaultdict(list)
    for i,r in enumerate(rows): groups[(r.get("country") or "__MISSING__") if by_country else "ALL"].append(i)
    null=defaultdict(list)
    for _ in range(n):
        mapping=list(range(len(rows)))
        for ids in groups.values():
            shuffled=ids[:]; rng.shuffle(shuffled)
            for src,dst in zip(ids,shuffled): mapping[src]=dst
        trial=[]
        for i,r in enumerate(rows):
            q=dict(r); b=rows[mapping[i]]
            for f in ("long_value","short_value","w_long","w_short","signed","activity"):
                q[f+"_b"]=b[f+"_b"]
            q["shared"]=q["activity_a"]>0 and q["activity_b"]>0
            q["opposite"]=q["signed_a"]*q["signed_b"]<0
            q["same_side"]=q["shared"] and not q["opposite"] and q["signed_a"]!=0 and q["signed_b"]!=0
            trial.append(q)
        m=metrics(trial)
        for k in ("signed_pearson","long_weighted_jaccard","short_weighted_jaccard"):
            if m[k] is not None: null[k].append(m[k])
    def p(k): return (1+sum(v>=observed[k] for v in null[k]))/(1+len(null[k]))
    return {"mode":"within_country" if by_country else "global","iterations":n,
            **{k+"_p_upper":p(k) for k in null},
            **{k+"_null_95pct":[quantile(v,.025),quantile(v,.975)] for k,v in null.items()}}


def synthetic_13f(rows):
    eligible=[(r.get("country") or "").upper()=="US" and bool(norm_id(r.get("cusip"))) for r in rows]
    visible={}
    masses={}
    for s in ("a","b"):
        x=[r[f"w_long_{s}"] if ok else 0.0 for r,ok in zip(rows,eligible)]; total=sum(x)
        masses[s]=total; visible[s]=[v/total if total else 0.0 for v in x]
    manager=[.5*(x+y) for x,y in zip(visible["a"],visible["b"])]
    signed=[r["common_signed"] for r in rows]
    full_long=[.5*(r["w_long_a"]+r["w_long_b"]) for r in rows]
    return {"mask":"US cash equity + CUSIP proxy; NOT Official 13(f) List",
            "eligible_count":sum(eligible),"visible_long_mass_a":masses["a"],"visible_long_mass_b":masses["b"],
            "visible_sibling_pearson":pearson(visible["a"],visible["b"]),
            "visible_sibling_spearman":pearson(rank(visible["a"]),rank(visible["b"])),
            "visible_sibling_weighted_jaccard":wj(visible["a"],visible["b"]),
            "visible_manager_vs_full_signed_pearson":pearson(manager,signed),
            "visible_manager_vs_full_signed_spearman":pearson(rank(manager),rank(signed)),
            "visible_manager_vs_full_long_pearson":pearson(manager,full_long)}


def write_csv(path, rows):
    if not rows:return
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--a",required=True); ap.add_argument("--b",required=True); ap.add_argument("--out",required=True); ap.add_argument("--permutations",type=int,default=5000)
    args=ap.parse_args(); out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    ma,ra=parse(Path(args.a)); mb,rb=parse(Path(args.b))
    if ma["report_date"]!=mb["report_date"]: raise RuntimeError(f"report date mismatch {ma['report_date']} {mb['report_date']}")
    ba,da=make_book(ra); bb,db=make_book(rb); rows=align(ba,bb)
    result={"status":"EXECUTED","gate":"PENDING_FACTOR_NEUTRAL_AND_CROSS_MANAGER_VALIDATION",
            "fund_a":{"meta":ma,"book":da},"fund_b":{"meta":mb,"book":db},
            "metrics":metrics(rows),"permutation_country":permute(rows,args.permutations,20260827,True),
            "synthetic_13f":synthetic_13f(rows),
            "discipline":{"direct_short_is_exposure_not_intent":True,"raw_similarity_is_not_common_alpha_proof":True}}
    write_csv(out/"aligned_books.csv",rows)
    write_csv(out/"top_common_long.csv",sorted(rows,key=lambda r:r["common_long"],reverse=True)[:50])
    write_csv(out/"top_common_short.csv",sorted(rows,key=lambda r:r["common_short"],reverse=True)[:50])
    write_csv(out/"largest_disagreements.csv",sorted(rows,key=lambda r:abs(r["signed_spread"]),reverse=True)[:100])
    (out/"metrics.json").write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n")
    (out/"report.md").write_text("# QLBI AQR sibling pilot\n\n```json\n"+json.dumps(result,indent=2,ensure_ascii=False)+"\n```\n")
    manifest={p.name:sha256(p) for p in out.iterdir() if p.is_file()}; (out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print(json.dumps(result,indent=2,ensure_ascii=False))

if __name__=="__main__": main()
