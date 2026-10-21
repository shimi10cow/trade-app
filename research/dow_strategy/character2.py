"""Pair character ruler v2 (2026-10-21). Measures the market behaviour each EA family relies on, from price only
(no EA results): forward move after an event, in the event's direction, in ATR(H1) units, over h M15 bars.
Reported: mean, standard error, first half (2005-2015) / second half (2016-2026), count. Run in each pair's workspace.
Families (M15 signal at the bar close; buy shown, sell mirrored):
  trend_drift      : every 16th M15 bar while the H1 major trend is up            -> does a trend keep going at all
  pb_stoch         : M15 stochastic buy sequence while H1 major up & H1 SMA20>75  -> pullback entry (T)
  pb_ma75          : H1 bar dips to H1 SMA75 and closes above it, H1 major up      -> pullback to the MA (EUR 'push')
  range_fade       : M15 stochastic signals while the H4 range score > 0.7         -> fade inside a range (R)
  turn_prov        : M15 provisional turn before the major turn (J base); +h4 / +h4+h1 / +h4+h1+0-10h
  turn_major_h1    : H1 major reversal
  cl15_break       : M15 correction line broken (C setup)
  bo_h1            : H1 major breakout (new high in an up trend)                   -> momentum after a breakout
Writes results/character2.csv"""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
import env_ctx as EC  # noqa: E402
B = X.B
C = B.c; N = len(C); T15 = B.T15; CL15 = X.CL15; C1 = B.C1; A1 = B.A1
h1c = B.h1.c.to_numpy(float); S20 = pd.Series(h1c).rolling(20).mean().to_numpy(); S75 = pd.Series(h1c).rolling(75).mean().to_numpy()
h1l = B.h1.l.to_numpy(float); h1h = B.h1.h.to_numpy(float)
K1 = np.clip(np.searchsorted(np.array(C1, dtype='datetime64[ns]'), CL15.to_numpy(), side='right') - 1, 0, len(C1) - 1)   # H1 bar closed by each M15 close
M15_OF_H1 = np.clip(CL15.searchsorted(pd.DatetimeIndex(C1)) , 0, N - 1)                                                  # M15 bar whose close = H1 close
EV = {}
def add(name, i, s):
    EV.setdefault(name, []).append((int(i), int(s)))
h1maj = [b[0] for b in B.R1['bars']]; h4prov = [b[0] for b in B.R4['prov_bars']]
C4 = np.array(B.C4, dtype='datetime64[ns]')
def h4p(i):
    k = np.searchsorted(C4, CL15[i].to_datetime64(), side='right') - 1
    return h4prov[k] if k >= 0 else None
start = CL15.searchsorted(B.START)
dirs = {'up': 1, 'down': -1}
for i in range(start, N, 16):
    d = h1maj[K1[i]]
    if d in dirs:
        add('trend_drift', i, dirs[d])
st = X.trigger('stoch')
for d, lst in st.items():
    s = dirs[d]
    for i in lst:
        if i < start: continue
        k = K1[i]
        if h1maj[k] == d and s * (S20[k] - S75[k]) > 0:
            add('pb_stoch', i, s)
        rs = EC.ctx_at(CL15[i], s)['rs']
        if np.isfinite(rs) and rs > 0.7:
            add('range_fade', i, s)
for k in range(200, len(h1c)):
    i = M15_OF_H1[k]
    if i < start: continue
    if h1maj[k] == 'up' and h1l[k] <= S75[k] < h1c[k]:
        add('pb_ma75', i, 1)
    if h1maj[k] == 'down' and h1h[k] >= S75[k] > h1c[k]:
        add('pb_ma75', i, -1)
for e in B.R15['prov_events']:
    if e['action'] not in ('REVERSAL', 'PROV_START'): continue
    i = e['idx']; to = e['to']
    if i < start or B.R15['bars'][i][0] == to: continue
    s = dirs[to]; add('turn_prov', i, s)
    if h4p(i) == to:
        add('turn_prov+h4', i, s)
        if h1maj[K1[i]] == to:
            add('turn_prov+h4+h1', i, s)
            hr = T15[i].hour
            add('turn_prov+h4+h1+0-10h' if hr < 10 else 'turn_prov+h4+h1+10-24h', i, s)
for e in B.R1['events']:
    if e.get('machine') != 'major': continue
    i = M15_OF_H1[e['idx']]
    if i < start: continue
    if e['action'] == 'REVERSAL':
        add('turn_major_h1', i, dirs[e['to']])
        if h4p(i) == e['to']: add('turn_major_h1+h4', i, dirs[e['to']])
    if e['action'] == 'BREAKOUT': add('bo_h1', i, dirs[e.get('to', h1maj[e['idx']])] if e.get('to', h1maj[e['idx']]) in dirs else 0)
import step2_newea as S2
for e in S2.cl15_events():
    i = CL15.searchsorted(e['t'])
    if start <= i < N: add('cl15_break', i, e['side'])
rows = []
for name, lst in EV.items():
    for h in (24, 96):
        v = []; yr = []
        for i, s in lst:
            if s == 0 or i + h >= N: continue
            a = A1[K1[i]]
            if not np.isfinite(a) or a <= 0: continue
            v.append(s * (C[i + h] - C[i]) / a); yr.append(T15[i].year)
        v = np.array(v); yr = np.array(yr)
        if not len(v): continue
        f = v[yr <= 2015]; g = v[yr >= 2016]
        rows.append(dict(family=name, h=h, n=len(v), mean=v.mean(), se=v.std() / np.sqrt(len(v)), first=f.mean() if len(f) else np.nan, second=g.mean() if len(g) else np.nan))
D = pd.DataFrame(rows).sort_values(['family', 'h'])
D.to_csv(B.HERE / 'results' / 'character2.csv', index=False)
pd.set_option('display.width', 200); print(D.round(3).to_string(index=False))
