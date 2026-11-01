import pandas as pd, numpy as np
from lab import *
rows = []
for sym in DEV + OOS:
    h, d = load(sym); L = legs(d); mid = h.t.iloc[len(h) // 2]; S1 = to_h1(h, state(d, 'ma'))
    tr = reentry2(h, S1, COST[sym], 'trail', 2.5, 20, key=sym); st = stats(tr)
    for k in ('ma', 'don'):
        lt = longhold(h, d, state(d, k), COST[sym]); s2 = stats(lt); a, cap = capture(lt, L); t = pd.to_datetime(lt.t)
        rows.append(dict(sym=sym, grp='作' if sym in DEV else '確', kind='長期_' + k, **s2, cap=cap, R1=lt.R[t < mid].mean(), R2=lt.R[t >= mid].mean()))
    t = pd.to_datetime(tr.t); a, cap = capture(tr, L)
    rows.append(dict(sym=sym, grp='作' if sym in DEV else '確', kind='押し目', **st, cap=cap, R1=tr.R[t < mid].mean(), R2=tr.R[t >= mid].mean()))
R = pd.DataFrame(rows); R.to_pickle('run4.pkl'); pd.set_option('display.width', 220)
for kind, g in R.groupby('kind'):
    print(f"\n== {kind}"); print(g[['sym', 'grp', 'n', 'per_y', 'win', 'avgR', 'sumR', 'dd', 'R1', 'R2', 'cap']].round(2).to_string(index=False))
    print('  まとめ: 平均R', round(g.avgR.mean(), 3), ' プラスの銘柄', f"{(g.avgR > 0).sum()}/{len(g)}", ' 合計', round(g.sumR.sum()))
