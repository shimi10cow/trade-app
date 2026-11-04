"""Broker-time (Europe/Athens) full-history live Frames from the research UTC M15 caches -> tz/frames_{sym}.pkl (2026-11-04)."""
import pickle, sys, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.core import Frames
s = sys.argv[1]
m = pd.read_pickle(f'/home/user/trendlab/stoch/m15_{s}.pkl').rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
if s.endswith('JPY'):
    for z in 'ohlc': m[z] = m[z] / 100
m['t'] = pd.to_datetime(m.t).dt.tz_localize('UTC').dt.tz_convert('Europe/Athens').dt.tz_localize(None)
m = m.drop_duplicates('t').sort_values('t').reset_index(drop=True)
F = Frames(m, '2005-01-01', h_days=10000, m_days=10000)
mb = F.m15_all.set_index('t'); F.W1 = mb.resample('W-MON', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
pickle.dump(F, open(f'/home/user/trendlab/tz/frames_{s}.pkl', 'wb')); print(s, 'ok', flush=True)
