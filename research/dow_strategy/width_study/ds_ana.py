import sys, pandas as pd, numpy as np
d = pd.concat([pd.read_pickle(f) for f in sys.argv[1:]]); d['tt'] = pd.to_datetime(d.t)
h = lambda x: x / pd.Timedelta('1h')
d['W_lr'] = h(d.tt - d.t_left); d['W_ln'] = h(d.t_neck - d.t_left); d['W_nr'] = h(d.tt - d.t_neck)
def table(g, title):
    mid = g.tt.median(); print(f"\n=== {title}: {len(g)} 回 平均 {g.R.mean():+.2f}R 合計 {g.R.sum():+.0f}R（前半 < {mid:%Y-%m}）")
    for col, lab in (('W_lr', '左肩→右肩'), ('W_ln', '左肩→ネック'), ('W_nr', 'ネック→右肩')):
        q = g[col].quantile([1/3, 2/3]).to_numpy(); b = pd.cut(g[col], [-1e9, q[0], q[1], 1e9], labels=['狭', '中', '広'])
        cells = []
        for k, x in g.groupby(b, observed=True):
            a, z = x[x.tt < mid], x[x.tt >= mid]
            cells.append(f"{k} {x.R.mean():+.2f}({len(x)}) 前{a.R.mean():+.2f}/後{z.R.mean():+.2f}")
        print(f"  {lab} 区切り{q[0]:.0f}/{q[1]:.0f}h: " + ' | '.join(cells))
for sym, g in d.groupby('sym'):
    table(g[g.adopted], f'{sym} 採用（深さ4以上・向き）')
    table(g, f'{sym} 絞り込み前（全部）')
g = d.copy(); table(g, '3 銘柄まとめて（全部）')
