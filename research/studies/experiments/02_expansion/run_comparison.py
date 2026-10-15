#!/usr/bin/env python3
"""Experiment 02: expansion exception ON vs OFF, with P3 simulated then excluded."""
import argparse
import subprocess
import sys
from pathlib import Path
import pandas as pd
import numpy as np

HERE=Path(__file__).resolve().parent
SHARED=HERE.parents[1]/"shared_backtest_20261014"
def metrics(df):
    r=df["R"].to_numpy(dtype=float)
    if not len(r): return dict(trades=0,total_R=0,pf=None,max_DD=None,win_rate=None)
    gains=r[r>0].sum(); losses=-r[r<0].sum()
    equity=np.r_[0,np.cumsum(r)]
    return dict(trades=len(r),total_R=float(r.sum()),pf=float(gains/losses) if losses else None,
                max_DD=float((equity-np.maximum.accumulate(equity)).min()),
                win_rate=float((r>0).mean()*100))
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-dir",type=Path,default=Path("/mnt/data"))
    args=ap.parse_args()
    HERE.mkdir(parents=True,exist_ok=True)
    runs={}
    for name,disable in (("ON","none"),("OFF","expansion")):
        cmd=[sys.executable,str(SHARED/"runner.py"),"--pair","EURUSD","--h4","off",
             "--p","p12","--disable",disable,"--data-dir",str(args.data_dir),"--tag","exp02"]
        subprocess.run(cmd,check=True)
        path=args.data_dir/"ea_cache"/f"EURUSD_off_p12_{disable}_exp02_trades.pkl"
        runs[name]=pd.read_pickle(path).sort_values("time")
    rows=[]
    for name,df in runs.items():
        for label,part in (("all",df),("2015+",df[df.time>=pd.Timestamp("2015-01-01")])):
            rows.append(dict(setting=name,period=label,**metrics(part)))
        for y,g in df.groupby(df.time.dt.year):
            rows.append(dict(setting=name,period=str(y),**metrics(g)))
    pd.DataFrame(rows).to_csv(HERE/"comparison.csv",index=False)
    a,b=runs["ON"],runs["OFF"]
    # Exception-only identification uses the engine's explicit B_exception marker.
    extra=a[a.B_exception.astype(bool)].copy()
    extra.to_csv(HERE/"exception_trades.csv",index=False)
    pd.DataFrame([dict(scope="exception-marked ON trades",**metrics(extra))]).to_csv(HERE/"exception_summary.csv",index=False)
    print(pd.DataFrame(rows).to_string(index=False))
    print("NOTE: exception-marked trades are not necessarily the entire causal ON/OFF difference.")
if __name__=="__main__":main()
