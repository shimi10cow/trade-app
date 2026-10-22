"""Workspace for a non-FX instrument (gold, BTC): prices are converted to natural log so that 1 'pip' (0.0001) = 0.01%
move at any price level (gold went 340 -> 4100, BTC 1,600 -> 120,000). The log is monotonic, so highs/lows, Dow pivots and
candle order are unchanged; ATR and costs become relative. Source = ForexTester-style M5 zip (UTC)."""
import sys, os, subprocess, zipfile
import numpy as np, pandas as pd
sym, src = sys.argv[1], sys.argv[2]
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
W = f'{S}/ws_{sym}'; R = '/home/user/trade-app/research'
os.makedirs(W + '/research', exist_ok=True); os.makedirs(W + '/cache', exist_ok=True)
subprocess.run(f"cd {R} && tar cf - --exclude=./archive --exclude=./datasets/raw --exclude=./dow_strategy/results --exclude=./dow_strategy/feedback --exclude=__pycache__ --exclude='./chart_lab/*.html' . | (cd {W}/research && tar xf -)", shell=True, check=True)
for d in ('results/step2', 'results/turn', 'results/session', 'results/pb'):
    os.makedirs(f'{W}/research/dow_strategy/{d}', exist_ok=True)
os.makedirs(W + '/research/datasets/raw/m5', exist_ok=True)
z = zipfile.ZipFile(src); d = pd.read_csv(z.open(z.namelist()[0]))
d['time'] = pd.to_datetime(d['<DTYYYYMMDD>'].astype(str) + d['<TIME>'].astype(str).str.zfill(4), format='%Y%m%d%H%M')
d = d.rename(columns={'<OPEN>': 'open', '<HIGH>': 'high', '<LOW>': 'low', '<CLOSE>': 'close'})
d = d[['time', 'open', 'high', 'low', 'close']].sort_values('time').drop_duplicates('time')
d = d[(d[['open', 'high', 'low', 'close']] > 0).all(axis=1)]
raw = d.copy()
for c in ('open', 'high', 'low', 'close'):
    d[c] = np.log(d[c]).round(6)
d.to_csv(f'{W}/research/datasets/raw/m5/{sym}_M5.csv.gz', index=False, compression='gzip')
raw.to_csv(f'{W}/{sym}_M5_raw.csv.gz', index=False, compression='gzip')
m = d.set_index('time').resample('15min', label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna().reset_index()
m.to_csv(f'{W}/research/datasets/derived/eurusd_m15/2026-10-19/EURUSD_M15_2003_2026.csv.gz', index=False, compression='gzip')
sys.path.insert(0, W + '/research')
from env_recognition.data import load_long_m15
b = load_long_m15().rename(columns=dict(t='time', o='open', h='high', l='low', c='close')); b.to_csv(f'{W}/M15_broker.csv', index=False)
print(sym, 'M5', len(d), 'M15', len(m), 'broker', len(b), b.time.iloc[0], b.time.iloc[-1], flush=True)
