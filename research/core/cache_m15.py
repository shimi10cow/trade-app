"""Build M15 OHLC cache from MT-style M1 ZIP in chunks; no lookahead."""
import argparse,json,zipfile
from pathlib import Path
import pandas as pd

def build(src:Path,dest:Path,chunksize=400_000):
    dest.parent.mkdir(parents=True,exist_ok=True)
    parts=[];carry=pd.DataFrame();n=0
    with zipfile.ZipFile(src) as z:
        names=[p for p in z.namelist() if p.lower().endswith(".csv")]
        if len(names)!=1:raise ValueError(f"Expected one CSV: {names}")
        with z.open(names[0]) as f:
            for chunk in pd.read_csv(f,chunksize=chunksize,usecols=["<DTYYYYMMDD>","<TIME>","<OPEN>","<HIGH>","<LOW>","<CLOSE>"]):
                t=pd.to_datetime(chunk["<DTYYYYMMDD>"].astype(str)+chunk["<TIME>"].astype(str).str.zfill(4),format="%Y%m%d%H%M")
                x=pd.DataFrame({"time":t.dt.floor("15min"),"open":chunk["<OPEN>"].values,"high":chunk["<HIGH>"].values,"low":chunk["<LOW>"].values,"close":chunk["<CLOSE>"].values})
                if not carry.empty:x=pd.concat([carry,x],ignore_index=True)
                last=x.time.iloc[-1];carry=x.loc[x.time.eq(last)].copy();x=x.loc[x.time.ne(last)]
                if not x.empty:parts.append(x.groupby("time",sort=True).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).reset_index())
                n+=len(chunk)
    if not carry.empty:parts.append(carry.groupby("time",sort=True).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).reset_index())
    out=pd.concat(parts,ignore_index=True).groupby("time",sort=True).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last")).reset_index()
    assert out.time.is_monotonic_increasing and out.time.is_unique
    out.to_pickle(dest)
    manifest={"source":str(src),"cache":str(dest),"source_m1_rows":n,"m15_rows":len(out),"start":str(out.time.iloc[0]),"end":str(out.time.iloc[-1]),"columns":list(out.columns),"timezone":"MT source time (not converted)"}
    dest.with_suffix(".json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    print(json.dumps(manifest,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source",required=True,type=Path);p.add_argument("--output",required=True,type=Path);a=p.parse_args();build(a.source,a.output)
