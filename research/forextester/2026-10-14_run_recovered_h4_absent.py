"""2026-10-14: reproduce recovered-engine H4-absent 23-year baseline.
Usage: python research/forextester/2026-10-14_run_recovered_h4_absent.py \
  --data ForexTester_VIP_EURUSD_USDJPY_M5_M15_2003_2026.zip \
  --engine research/backtest_recovery/full_backtest_engine_v1_recovered.py \
  --out results
Requires pandas and numpy. This is an ablation, NOT the full original/current EA.
"""
import argparse, gzip, importlib.util, sys, zipfile
from pathlib import Path
import pandas as pd
import numpy as np

def metrics(frame):
    r=frame['R'].to_numpy(dtype=float)
    gains=r[r>0].sum(); losses=-r[r<0].sum()
    eq=np.r_[0,np.cumsum(r)]
    return {'trades':len(r),'net_R':round(float(r.sum()),3),
            'PF':round(float(gains/losses),3) if losses else None,
            'win_rate_pct':round(float((r>0).mean()*100),2) if len(r) else None,
            'max_dd_R':round(float((eq-np.maximum.accumulate(eq)).min()),3)}

def main():
    a=argparse.ArgumentParser()
    a.add_argument('--data',type=Path,required=True)
    a.add_argument('--engine',type=Path,required=True)
    a.add_argument('--out',type=Path,default=Path('results'))
    args=a.parse_args()
    args.out.mkdir(parents=True,exist_ok=True)
    spec=importlib.util.spec_from_file_location('recovered_ea',args.engine)
    e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)
    archive=zipfile.ZipFile(args.data)
    def load(pair):
        with archive.open(f'{pair}_M15_UTC.csv.gz') as f:
            d=pd.read_csv(gzip.GzipFile(fileobj=f),usecols=['time_utc','open','high','low','close'],parse_dates=['time_utc'])
        d['time']=d.pop('time_utc').dt.tz_localize(None)
        return d[['time','open','high','low','close']]
    e.load_m15=load
    e.load_levels=lambda pair:pd.DataFrame(columns=['active_time','expiry_time','price'])
    e.structural_level_reject=lambda *args,**kwargs:False
    result=[]
    for pair in ('EURUSD','USDJPY'):
        print('Running',pair,flush=True)
        tr=e.run_pair(pair)
        tr.to_csv(args.out/f'2026-10-14_{pair}_h4_absent_trades.csv',index=False)
        result.append({'pair':pair,**metrics(tr)})
        print(result[-1],flush=True)
    pd.DataFrame(result).to_csv(args.out/'2026-10-14_h4_absent_summary.csv',index=False)

if __name__=='__main__':
    main()
