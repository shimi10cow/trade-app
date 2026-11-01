import sys, pandas as pd, numpy as np, time
from lab import *
grp = sys.argv[1]; syms = DEV if grp == 'dev' else OOS; k = sys.argv[2] if len(sys.argv) > 2 else 'ma'
variants = [(x, dp, lk) for x in ('tp2', 'trail') for dp in (1.5, 2.5, 4.0) for lk in (20, 50)]
rows = []
for sym in syms:
    h, d = load(sym); L = legs(d); S1 = to_h1(h, state(d, k)); mid = h.t.iloc[len(h) // 2]
    for x, dp, lk in variants:
        tr = reentry2(h, S1, COST[sym], x, dp, lk, key=sym); st = stats(tr); a, cap = capture(tr, L)
        t = pd.to_datetime(tr.t) if len(tr) else pd.Series(dtype='datetime64[ns]')
        rows.append(dict(sym=sym, exit=x, depth=dp, look=lk, **st, legs_in=a, cap=cap, R1=tr.R[t < mid].mean() if len(tr) else np.nan, R2=tr.R[t >= mid].mean() if len(tr) else np.nan))
R = pd.DataFrame(rows); R.to_pickle(f're2_{grp}_{k}.pkl'); pd.set_option('display.width', 220)
g = R.groupby(['exit', 'depth', 'look']).agg(n=('n', 'sum'), per_y=('per_y', 'mean'), win=('win', 'mean'), avgR=('avgR', 'mean'), sumR=('sumR', 'sum'),
                                          dd=('dd', 'mean'), R1=('R1', 'mean'), R2=('R2', 'mean'), plus=('avgR', lambda x: (x > 0).mean()), cap=('cap', 'mean'))
print(g.round(2).to_string())
