import pandas as pd, numpy as np
for f in ('dow/dow_J2.pkl', 'dow/dow_T2.pkl'):
    g = pd.read_pickle(f); mid = g.tt.median(); print(f"\n=== {g.key.iat[0]}: {len(g)} 回 平均 {g.R.mean():+.2f}R 合計 {g.R.sum():+.0f}R（前半 < {mid:%Y-%m}）")
    for col, lab in (('W15', 'M15 の直近の波の幅'), ('W1', 'H1 の直近の波の幅'), ('W4', 'H4 の直近の波の幅')):
        q = g[col].quantile([1/3, 2/3]).to_numpy(); b = pd.cut(g[col], [-1e9, q[0], q[1], 1e9], labels=['狭', '中', '広'])
        cells = [f"{k} {x.R.mean():+.2f}({len(x)}) 前{x[x.tt<mid].R.mean():+.2f}/後{x[x.tt>=mid].R.mean():+.2f}" for k, x in g.groupby(b, observed=True)]
        print(f"  {lab}（本）区切り{q[0]:.0f}/{q[1]:.0f}: " + ' | '.join(cells))
