"""Which shape-exit firings help? Split the gain (new R - original R) by the higher-TF state at the moment it fires."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape2 as S2  # noqa: E402
import env_ctx as EC  # noqa: E402
S1 = S2.S1; B = S1.B; T = S1.T; C, N, COST = S2.C, S2.N, S2.COST
C1 = list(B.C1); C4 = list(B.C4)
S2.AWIN = 384
TR, yrs = S1.load_all()
rows = []
for nm, t in TR.items():
    for x in t.itertuples():
        i = S2.shape_exit(x, 0.7, 0.3, 0)
        if i is None:
            continue
        nr = x.side * (C[i] - x.entry) / x.risk - COST / x.risk
        tc = T[i] + pd.Timedelta(minutes=15)
        k1 = bisect.bisect_right(C1, tc) - 1; k4 = bisect.bisect_right(C4, tc) - 1
        d = 'up' if x.side == 1 else 'down'
        f = lambda b: 'with' if b == d else ('none' if b not in ('up', 'down') else 'against')
        cx = EC.ctx_at(tc, x.side)
        rebound = abs(x.entry - (B.l[max(0, x.i0 - 384):x.i0].min() if x.side == -1 else B.h[max(0, x.i0 - 384):x.i0].max())) / x.risk
        rows.append(dict(ea=nm, gain=nr - x.R, newR=nr, origR=x.R, h1=f(B.R1['bars'][k1][0]), h1p=f(B.R1['prov_bars'][k1][0]),
                         h4=f(B.R4['bars'][k4][0]), h4p=f(B.R4['prov_bars'][k4][0]), rs=cx.get('rs'), dA=rebound, bars=i - x.i0))
d = pd.DataFrame(rows)
print('発動', len(d), '平均の差', round(d.gain.mean(), 3))
for c in ('ea', 'h1', 'h1p', 'h4', 'h4p'):
    print(d.groupby(c).gain.agg(['count', 'sum', 'mean']).round(2).to_string(), '\n')
d['rsq'] = pd.qcut(d.rs, 3); d['dAq'] = pd.qcut(d.dA, 3); d['barsq'] = pd.qcut(d.bars, 3)
for c in ('rsq', 'dAq', 'barsq'):
    print(d.groupby(c, observed=True).gain.agg(['count', 'sum', 'mean']).round(2).to_string(), '\n')
print(d.groupby(['h1p', 'h4p']).gain.agg(['count', 'sum', 'mean']).round(2).to_string())
