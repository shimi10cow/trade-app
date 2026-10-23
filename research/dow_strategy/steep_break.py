"""H1 steep trendline break -> stop entering in that direction for a while (user idea, 2026-10-23).
Up line = through the last two confirmed H1 swing lows (newer one higher), known at the H1 close; its slope per H1 bar in
units of ATR(H1). A CLOSE below the line while slope >= k -> 'steep up line broken' -> longs blocked for N hours.
Mirror for down lines (swing highs) and shorts. k = 0.05 / 0.10 / 0.20, N = 12 / 24 / 48.
Checked on every EA trade of this workspace's instrument (master table): blocked trades' R by half.
Run inside a workspace (EURUSD = main). Writes feat/steep_<SYM>.pkl"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SYM = os.environ.get('M5_SYM', 'EURUSD')
h1 = B.h1.reset_index(drop=True); C1 = pd.DatetimeIndex(B.C1); c = h1.c.to_numpy(float); A = np.asarray(B.A1, float)
piv = sorted((e['available_idx'], e['idx'], e['kind'], e['price']) for e in B.R1['pivot_events'])
breaks = []                                   # (time, side_blocked, slope)
lows, highs = [], []; pi = 0; done = set()
for i in range(len(h1)):
    while pi < len(piv) and piv[pi][0] <= i:
        av, ix, kind, pr = piv[pi]; pi += 1
        (lows if kind == 'lo' else highs).append((ix, pr))
    for side, pts in ((1, lows), (-1, highs)):
        if len(pts) < 2: continue
        (i1, p1), (i2, p2) = pts[-2], pts[-1]
        if i2 <= i1 or (side == 1 and p2 <= p1) or (side == -1 and p2 >= p1): continue
        key = (side, i1, i2)
        if key in done: continue
        a = A[i] if np.isfinite(A[i]) and A[i] > 0 else np.nan
        sl = (p2 - p1) / (i2 - i1); v = p2 + sl * (i - i2)
        if (side == 1 and c[i] < v) or (side == -1 and c[i] > v):
            seg = np.arange(i2, i); away = (side * (c[seg] - (p2 + sl * (seg - i2)))).max() / a if len(seg) else 0
            done.add(key); breaks.append((C1[i], side, abs(sl) / a, away, i - i1))
BR = pd.DataFrame(breaks, columns=['t', 'side', 'slope', 'away', 'age'])
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl'); T = T[T.pair == SYM][['key', 'tt', 'side', 'R', 'half']].copy()
if SYM in ('XAUUSD', 'USDJPY'):
    Q = pd.read_pickle(f'{S}/feat/q_best.pkl'); Q = Q[Q.pair == SYM].assign(key=f'Q@{SYM}', half=lambda d: np.where(d.tt.dt.year <= 2015, 1, 2))
    T = pd.concat([T, Q[['key', 'tt', 'side', 'R', 'half']]], ignore_index=True)
T['tt'] = pd.to_datetime(T.tt)
rows = []
for k in (0.10, 0.20):
  for aw in (2, 3):
    for N in (24, 48):
        b = BR[(BR.slope >= k) & (BR.away >= aw) & (BR.age >= 10)]
        blk = np.zeros(len(T), bool)
        for sd in (1, -1):
            bt = b[b.side == sd].t.to_numpy(); m = (T.side == sd).to_numpy(); tt = T.tt.to_numpy()[m]
            j = np.searchsorted(bt, tt, 'right') - 1
            ok = (j >= 0) & ((tt - bt[np.maximum(j, 0)]) <= np.timedelta64(N, 'h'))
            blk[np.nonzero(m)[0][ok]] = True
        for h in (1, 2):
            x = T[(T.half == h).to_numpy()]; bb = blk[(T.half == h).to_numpy()]
            rows.append(dict(sym=SYM, k=k, aw=aw, nb=len(b), N=N, half=h, n=int(bb.sum()), blockedR=x.R[bb].sum(), blocked_mean=x.R[bb].mean(), rest_mean=x.R[~bb].mean()))
D = pd.DataFrame(rows); D.to_pickle(f'{S}/feat/steep_{SYM}.pkl'); BR.to_pickle(f'{S}/feat/steep_breaks_{SYM}.pkl')
print(SYM, 'ブレイク数', len(BR), '傾き中央', round(BR.slope.median(), 3))
print(D.pivot_table(index=['k', 'aw', 'nb', 'N'], columns='half', values=['n', 'blockedR', 'blocked_mean', 'rest_mean']).round(2).to_string())
