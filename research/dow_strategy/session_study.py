"""Session character in JAPAN time (2026-10-21). Run in each pair's workspace.
Buckets (JST): 0-3, 3-6, 6-9, 9-12, 12-15, 15-18, 18-21, 21-24.
  activity     : mean |M15 body| / ATR(H1)
  impulse      : after a 1-hour move (4 M15 bars) of >= 1 ATR(H1), the next 2 hours in the same direction (ATR(H1)):
                 > 0 momentum (follow), < 0 reversion (range-like)
  turn_follow  : after an M15 provisional turn made before the major turn, H4 provisional same, next 6h / 24h
  bo_follow    : after an H1 major breakout, next 6h / 24h ; fake rate (back through within 4 H1 bars)
Halves 2005-2015 / 2016-2026 reported for stability. Writes results/session.csv"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
m15 = B.m15; T15 = pd.DatetimeIndex(B.T15); O, H, L, C = (m15[z].to_numpy(float) for z in 'ohlc'); N = len(C)
CL15 = X.CL15; C1 = np.array(B.C1, dtype='datetime64[ns]'); K1 = np.clip(np.searchsorted(C1, CL15.to_numpy(), side='right') - 1, 0, len(C1) - 1); a1 = B.A1[K1]
jst = (T15.tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').tz_convert('Asia/Tokyo')).hour.to_numpy()
jst = np.where(pd.isna(jst), -1, jst).astype(int)
def bk(h): return -1 if h < 0 else (h // 3) * 3
B3 = np.array([bk(h) for h in jst]); YR = T15.year.to_numpy()
start = CL15.searchsorted(B.START)
rows = []
def add(kind, i, val, extra=None):
    if i >= start and B3[i] >= 0 and np.isfinite(val): rows.append((kind, B3[i], YR[i], val, extra))
ok = np.arange(N) >= start
for i in range(start, N):
    if a1[i] > 0: add('activity', i, abs(C[i] - O[i]) / a1[i])
for i in range(start + 4, N - 8):
    m = (C[i] - C[i - 4]) / a1[i]
    if abs(m) >= 1.0:
        add('impulse', i, np.sign(m) * (C[i + 8] - C[i]) / a1[i])
C4 = np.array(B.C4, dtype='datetime64[ns]'); h4p = [b[0] for b in B.R4['prov_bars']]
for e in B.R15['prov_events']:
    if e['action'] not in ('REVERSAL', 'PROV_START'): continue
    i = e['idx']; to = e['to']
    if i + 96 >= N or B.R15['bars'][i][0] == to: continue
    k4 = np.searchsorted(C4, CL15[i].to_datetime64(), side='right') - 1
    if k4 < 0 or h4p[k4] != to: continue
    s = 1 if to == 'up' else -1
    add('turn6h', i, s * (C[i + 24] - C[i]) / a1[i]); add('turn24h', i, s * (C[i + 96] - C[i]) / a1[i])
M15_OF_H1 = np.clip(CL15.searchsorted(pd.DatetimeIndex(B.C1)), 0, N - 1); h1c = B.h1.c.to_numpy(float); h1maj = [b[0] for b in B.R1['bars']]
for e in B.R1['events']:
    if e.get('machine') == 'major' and e['action'] == 'BREAKOUT':
        k = e['idx']; i = M15_OF_H1[k]; d = h1maj[k]
        if d not in ('up', 'down') or i + 96 >= N or k < 1: continue
        s = 1 if d == 'up' else -1
        add('bo6h', i, s * (C[i + 24] - C[i]) / a1[i]); add('bo24h', i, s * (C[i + 96] - C[i]) / a1[i])
        add('bo_fake', i, float(any(s * (h1c[k + j] - h1c[k - 1]) < 0 for j in range(1, 5) if k + j < len(h1c))))
D = pd.DataFrame(rows, columns=['kind', 'jst', 'y', 'v', 'x'])
g = D.groupby(['kind', 'jst']).agg(n=('v', 'size'), mean=('v', 'mean'), se=('v', lambda s: s.std() / np.sqrt(len(s))),
                                     first=('v', lambda s: s[D.loc[s.index, 'y'] <= 2015].mean()), second=('v', lambda s: s[D.loc[s.index, 'y'] >= 2016].mean()))
g = g.reset_index(); g.to_csv(B.HERE / 'results' / 'session.csv', index=False)
pd.set_option('display.width', 200)
for k in ('activity', 'impulse', 'turn6h', 'turn24h', 'bo6h', 'bo24h', 'bo_fake'):
    x = g[g.kind == k].set_index('jst')
    print(k.ljust(9), '  '.join(f"{j:02d}-{j + 3:02d}:{x.loc[j, 'mean']:+.2f}({x.loc[j, 'first']:+.2f}/{x.loc[j, 'second']:+.2f})" for j in x.index))
