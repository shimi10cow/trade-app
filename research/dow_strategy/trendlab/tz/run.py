"""Time zone check (2026-11-04): the research M15 caches (stoch/m15_*.pkl) are in UTC, the live runner uses XM broker time
(Europe/Athens, UTC+2/+3, EU DST rules: shown by matching XM US30 bars). Rebuild the full-history Frames with broker-time
timestamps and run the live EAs of the symbol; compare with the UTC-based results. Usage: python run.py EURUSD
"""
import pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.core import Frames
from mt5_ea.live.env import Env
from mt5_ea.live.registry import ADOPTED
sym = sys.argv[1]
m = pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
if sym == 'USDJPY':
    for z in 'ohlc': m[z] = m[z] / 100
m['t'] = pd.to_datetime(m.t).dt.tz_localize('UTC').dt.tz_convert('Europe/Athens').dt.tz_localize(None)
m = m.drop_duplicates('t').sort_values('t').reset_index(drop=True)
F = Frames(m, '2005-01-01', h_days=10000, m_days=10000); env = Env(F.m15_all)
mb = F.m15_all.set_index('t'); F.W1 = mb.resample('W-MON', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
F0 = pickle.load(open(f'/home/user/trendlab/live_frames_{sym}.pkl', 'rb')); env0 = Env(F0.m15_all)
m0 = F0.m15_all.set_index('t'); F0.W1 = m0.resample('W-MON', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
rows = []
for e in ADOPTED:
    if e.symbol != sym or e.key in ('A@EURUSD', 'R@EURUSD'): continue
    for lab, FF, ee in (('UTC', F0, env0), ('broker', F, env)):
        tr = e.run(FF, ee)['trades']
        if not len(tr): continue
        tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]; t = pd.to_datetime(tr[tc]); x = tr[t >= '2005-06-01']
        r = x.R.astype(float)
        rows.append(dict(ea=e.key, data=lab, n=len(r), avg=r.mean(), t=r.mean() / (r.std(ddof=1) / np.sqrt(len(r))), tot=r.sum()))
        print(e.key, lab, len(r), f'{r.mean():+.3f}', flush=True)
pd.DataFrame(rows).to_pickle(f'/home/user/trendlab/tz/tz_{sym}.pkl'); print('done', sym)
