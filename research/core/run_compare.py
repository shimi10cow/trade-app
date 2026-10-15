"""Run repeatable A1/A2 ON/OFF experiments using one frozen M15 engine."""
import argparse,sys,json
from pathlib import Path
import pandas as pd
from dataclasses import replace
from engine_m15 import Config,run_pair,metrics

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--test",choices=["A1","A2"],required=True)
    ap.add_argument("--cache",type=Path,default=Path("/mnt/data/ea_shared/EURUSD2003_M15.pkl"))
    ap.add_argument("--output",type=Path,default=Path("/mnt/data/ea_shared/results"))
    args=ap.parse_args()
    # Optional cache path; engine also searches /mnt/data for pre-existing caches.\n    if args.cache.is_file():\n        import os\n        os.environ["EA_M15_CACHE"]=str(args.cache)
    import engine_m15 as engine
    engine.ROOT=Path("/mnt/data")\n    args.output.mkdir(parents=True,exist_ok=True)
    baseline=Config()
    assert not baseline.use_expansion_exception and baseline.use_delayed_zz
    assert not baseline.use_h4_levels and not baseline.use_h4_rsi and not baseline.use_inverse_trend
    assert baseline.max_entry_point==2 and baseline.max_positions==2
    allsum=[]
    for label,value in (("ON",0.00002 if args.test=="A1" else 0.25),("OFF",0.0)):
        cfg=replace(baseline,**({"s200_min":value} if args.test=="A1" else {"ma200_480_tol_atr":value}))
        print(f"RUN {args.test} {label}={value}",flush=True)
        trades=run_pair("EURUSD",cfg)
        trades.to_csv(args.output/f"{args.test}_{label}_trades.csv",index=False)
        for scope,d in [("ALL",trades),("2015+",trades.loc[pd.to_datetime(trades.time)>=pd.Timestamp("2015-01-01")])]:
            allsum.append({"test":args.test,"variant":label,"scope":scope,**metrics(d)})
        for yr,g in trades.groupby(pd.to_datetime(trades.time).dt.year):
            allsum.append({"test":args.test,"variant":label,"scope":str(yr),**metrics(g)})
    summary=pd.DataFrame(allsum)
    summary.to_csv(args.output/f"{args.test}_summary.csv",index=False)
    print(summary.loc[summary.scope.isin(["ALL","2015+"])].to_string(index=False))
    (args.output/f"{args.test}_settings.json").write_text(json.dumps({"test":args.test,"baseline":vars(baseline),"cache":str(args.cache) if args.cache.is_file() else "auto-discovered under /mnt/data","note":"Reconstructed canonical engine; not independently verified against live EA"},indent=2),encoding="utf-8")
if __name__=="__main__":main()
