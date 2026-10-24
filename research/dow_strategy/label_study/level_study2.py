"""H4 protected-level touch in an H4 trend, split by the D1 major Dow direction (user: 'it holds when the daily points that way')."""
import json, glob, numpy as np, pandas as pd
from level_study import VD, S, load, outcome
def d1dir(pair):
    P = {}
    for f in sorted(glob.glob(f'{S}/{VD[pair]}/data/[12][0-9][0-9][0-9].json')):
        for q in json.load(open(f))['D1']['prot']: P[q[0]] = q[2]
    t = np.array(sorted(P)); return t, np.array([P[x] for x in t], dtype=object)
rows = []
for pair in VD:
    b, _ = load(pair); T = b.index.values; H = b.h.values; L = b.l.values; C = b.c.values; A = b.atr.values; PP = b.pp.values; PD = b.pd.values
    dt, dd = d1dir(pair); yr = pd.to_datetime(T, unit='s').year; half = np.where(yr <= (2021 if pair == 'BTCUSD' else 2015), 1, 2); last = -999
    for j in range(20, len(T)):
        d = PD[j]; P = PP[j]
        if d not in ('up', 'down') or P is None or j - last < 12: continue
        s = 1 if d == 'up' else -1
        if (L[j] <= P + 0.5 * A[j] and C[j] > P) if s == 1 else (H[j] >= P - 0.5 * A[j] and C[j] < P):
            last = j; k = np.searchsorted(dt + 86400, T[j] + 14400, 'right') - 1; d1 = dd[k] if k >= 0 else None
            rows.append((pair, half[j], 'D1同じ向き' if d1 == d else 'D1逆向き' if d1 in ('up', 'down') else 'D1なし', outcome(H, L, C, A, j + 1, P, s)))
R = pd.DataFrame(rows, columns=['pair', 'half', 'd1', 'hold']).dropna()
print(R.groupby(['d1', 'half']).hold.agg(['mean', 'size']).unstack('half').round(2).to_string())
print(R.groupby(['pair', 'd1', 'half']).hold.mean().unstack(['d1', 'half']).round(2).to_string())
