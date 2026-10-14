"""Forex Tester EURUSD M1 to causal timeframe cache (2026-10-14)."""
import argparse
import zipfile
from pathlib import Path
import pandas as pd

def run(source, output):
    output.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as archive:
        with archive.open(archive.namelist()[0]) as stream:
            df = pd.read_csv(stream, usecols=[1,2,3,4,5,6],
                dtype={1:"int32",2:"int16",3:"float64",4:"float64",5:"float64",6:"float64"})
    df.columns=["date","time","open","high","low","close"]
    ts=pd.to_datetime(df.date.astype(str)+df.time.astype(str).str.zfill(4),format="%Y%m%d%H%M")
    df=df.set_index(ts)[["open","high","low","close"]].sort_index()
    if df.index.has_duplicates: raise ValueError("Duplicate M1 timestamps")
    for frequency,label in [("5min","M5"),("15min","M15"),("1h","H1"),("4h","H4")]:
        bars=df.resample(frequency,label="left",closed="left").agg(
            {"open":"first","high":"max","low":"min","close":"last"}).dropna()
        bars["available_at"]=bars.index+pd.Timedelta(frequency)
        target=output/f"EURUSD_{label}_OHLC_20261014.pkl"
        bars.to_pickle(target)
        print(label,len(bars),bars.index.min(),bars.index.max(),target)
    print("Causal usage: indicators from a bar are available only at available_at.")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--zip",type=Path,required=True)
    parser.add_argument("--out",type=Path,default=Path("cache"))
    args=parser.parse_args()
    run(args.zip,args.out)
