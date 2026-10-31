import sys, pandas as pd, numpy as np
d = pd.concat([pd.read_pickle(f'oos_{s}.pkl') for s in sys.argv[1:]]); d['tt'] = pd.to_datetime(d.t)
def cell(x, mid):
    if len(x) == 0: return '—'
    return f"{x.R.mean():+.2f}R×{len(x)}（前{x[x.tt<mid].R.mean():+.2f}/後{x[x.tt>=mid].R.mean():+.2f}）"
for scope, g0 in (('本番と同じ条件（深さ4以上・横幅24h）', d[d.adopted]), ('絞り込み前の全部', d)):
    print(f"\n## {scope}")
    for sym, g in list(g0.groupby('sym')) + ([('まとめ', g0)] if g0.sym.nunique() > 1 else []):
        mid = g.tt.median(); c = g.h4 == 'counter'
        print(f"  {sym:7s} H4逆向き {cell(g[c], mid)}  |  それ以外 {cell(g[~c], mid)}  差 {g[c].R.mean() - g[~c].R.mean():+.2f}R")
