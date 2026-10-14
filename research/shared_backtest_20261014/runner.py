#!/usr/bin/env python3
"""Shared reproducible ablation runner. See README.md. Requires NumPy/Pandas/Numba.
Use --baseline first; independent experiments should use unique --tag values.
"""
import argparse, bisect, importlib.util, pickle, sys, time, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

p=argparse.ArgumentParser()
p.add_argument('--pair',choices=['EURUSD','USDJPY'],required=True)
p.add_argument('--h4',choices=['off','on'],default='off')
p.add_argument('--p',choices=['p12','all','p1'],default='p12')
p.add_argument('--disable',choices=['none','q75','h4_rsi','ma_abcd','inverse_h1','expansion','delayed_zz','p3_mfe'],default='none')
p.add_argument('--data-dir',type=Path,default=Path('/mnt/data'))
p.add_argument('--tag',default='baseline')
args=p.parse_args()
root=args.data_dir; cache_dir=root/'ea_cache'; cache_dir.mkdir(parents=True,exist_ok=True)
version='engine-v1-fastpivot-v1-20261014'
engine_file=Path(__file__).resolve().parent/'engine.py'
spec=importlib.util.spec_from_file_location('ea_shared_engine',engine_file)
e=importlib.util.module_from_spec(spec);sys.modules[spec.name]=e;spec.loader.exec_module(e)
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fastpivot_patch import fast
e.causal_pivots_bootstrap=fast
cache=cache_dir/f'{args.pair}_2003_2026_{version}.pkl'
start=time.perf_counter()
if cache.exists():
 with cache.open('rb') as f:features=pickle.load(f)
else:
 zfile=root/f'{args.pair}2003.M1.zip'
 if not zfile.exists():raise SystemExit(f'Missing raw data: {zfile}')
 with zipfile.ZipFile(zfile) as z:
  with z.open(z.namelist()[0]) as f:
   d=pd.read_csv(f,usecols=[1,2,3,4,5,6],dtype={1:'int32',2:'int16',3:'float64',4:'float64',5:'float64',6:'float64'})
 d.columns=['date','clock','open','high','low','close']
 d['time']=pd.to_datetime(d.date.astype(str)+d.clock.astype(str).str.zfill(4),format='%Y%m%d%H%M')
 m=d.set_index('time')[['open','high','low','close']].resample('15min',label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna().reset_index()
 e.load_m15=lambda pair:m
 features=e.build_features(args.pair)
 with cache.open('wb') as f:pickle.dump(features,f,pickle.HIGHEST_PROTOCOL)
e.build_features=lambda pair,cfg=e.CFG:features
if args.h4=='off':
 e.load_levels=lambda pair:pd.DataFrame(columns=['price','created_time','active_time','side','expiry_time'])
 e.structural_level_reject=lambda *a,**k:False
else:
 levels_file=root/f'h4ext_{args.pair}_levels_2003_2026.csv'
 if not levels_file.exists():raise SystemExit(f'Missing H4 levels: {levels_file}')
 levels=pd.read_csv(levels_file)
 for col in ['created_time','active_time','expiry_time']:levels[col]=pd.to_datetime(levels[col])
 e.load_levels=lambda pair:levels
 price=levels.price.to_numpy();active=levels.active_time.to_numpy();expiry=levels.expiry_time.to_numpy()
 def reject(levels,t,entry,side,h4atr,cfg):
  if not np.isfinite(h4atr) or h4atr<=0:return False
  mask=(active<=np.datetime64(t))&(expiry>np.datetime64(t))
  if side==1:mask&=(price>entry)&(price-entry<=cfg.h4_level_tol_atr*h4atr)
  else:mask&=(price<entry)&(entry-price<=cfg.h4_level_tol_atr*h4atr)
  return bool(mask.any())
 e.structural_level_reject=reject
# Non-mutating experiment isolation: each process imports a fresh engine.
switches={'q75':'use_q75','h4_rsi':'use_h4_rsi','ma_abcd':'use_ma_abcd','inverse_h1':'use_inverse_h1','expansion':'use_expansion_exception','delayed_zz':'use_delayed_zz','p3_mfe':'use_p3_mfe'}
if args.disable!='none':setattr(e.CFG,switches[args.disable],False)
# P1/P2 filtering after execution is diagnostic only; it is NOT a
# re-simulation because omitted P3 positions can affect position limits.
tr=e.run_pair(args.pair).sort_values('time').reset_index(drop=True)
if args.p!='all':
 print('WARNING: P filter is post-trade diagnostic only; not a true P-limited backtest.',flush=True)
 tr=tr[tr.point.isin([1] if args.p=='p1' else [1,2])].copy()
out=cache_dir/f'{args.pair}_{args.h4}_{args.p}_{args.disable}_{args.tag}_trades.pkl'
tr.to_pickle(out)
for year in (2003,2015):
 subset=tr[tr.time>=pd.Timestamp(f'{year}-01-01')]
 print('RESULT',year,e.metrics(subset),flush=True)
print('saved',out,'elapsed_seconds',round(time.perf_counter()-start,2),flush=True)

annual=[{'year':int(y),**e.metrics(g.sort_values('time'))} for y,g in tr.groupby(tr.time.dt.year)]
pd.DataFrame(annual).to_csv(cache_dir/f'{args.pair}_{args.h4}_{args.p}_{args.disable}_{args.tag}_annual.csv',index=False)
