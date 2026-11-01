import sys, pandas as pd, numpy as np, time
from lab import *
grp = sys.argv[1]; syms = DEV if grp == 'dev' else OOS
variants = [(k, x, hl) for k in sys.argv[2].split(',') for x in sys.argv[3].split(',') for hl in (True, False)]
rows = []; t0 = time.time()
for sym in syms:
    h, d = load(sym); L = legs(d); ST = {k: to_h1(h, state(d, k)) for k in {v[0] for v in variants}}
    mid = h.t.iloc[len(h) // 2]
    for k, x, hl in variants:
        tr = reentry(h, ST[k], COST[sym], x, hl, key=sym)
        st = stats(tr); a, cap = capture(tr, L)
        h1, h2 = (tr[pd.to_datetime(tr.t) < mid], tr[pd.to_datetime(tr.t) >= mid]) if len(tr) else (tr, tr)
        rows.append(dict(sym=sym, state=k, exit=x, hl=hl, **st, legs_in=a, cap=cap, R1=h1.R.mean() if len(h1) else np.nan, R2=h2.R.mean() if len(h2) else np.nan))
    print(sym, f'{time.time() - t0:.0f}s', flush=True)
R = pd.DataFrame(rows); R.to_pickle(f're_{grp}.pkl'); pd.set_option('display.width', 220)
g = R.groupby(['state', 'exit', 'hl']).agg(n=('n', 'sum'), per_y=('per_y', 'mean'), win=('win', 'mean'), avgR=('avgR', 'mean'), sumR=('sumR', 'sum'),
                                          dd=('dd', 'mean'), R1=('R1', 'mean'), R2=('R2', 'mean'), plus=('avgR', lambda x: (x > 0).mean()), legs_in=('legs_in', 'mean'), cap=('cap', 'mean'))
print(g.round(2).to_string())
