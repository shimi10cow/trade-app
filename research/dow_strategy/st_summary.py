"""Summarise st_trend.py results per instrument (instrument split + realistic cost; top-5 dependence)."""
import sys, glob, numpy as np, pandas as pd
from pathlib import Path
CFG = {'XAUUSD': ((2005, 2015), (2016, 2026), 2.5), 'BTCUSD': ((2017, 2021), (2022, 2026), 8.0)}
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
sym, D = sys.argv[1], Path(sys.argv[2]); h1, h2, c = CFG[sym]; rows = []
for f in sorted(D.glob('S_*.csv')):
    d = pd.read_csv(f, parse_dates=['t'])
    if not len(d): continue
    R = d.R - (c - 1.2) * 1e-4 / d.risk; y = d.t.dt.year
    a = R[(y >= h1[0]) & (y <= h1[1])]; b = R[(y >= h2[0]) & (y <= h2[1])]; allr = R[y >= h1[0]]
    top = allr.sort_values(ascending=False).head(5).sum()
    eq = allr[np.argsort(d.t[y >= h1[0]].to_numpy())].cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(eq)).min()
    rows.append(dict(name=f.stem[2:], n=len(allr), a=a.sum(), pa=pf(a), b=b.sum(), pb=pf(b), dd=dd, ex5=allr.sum() - top))
T = pd.DataFrame(rows).sort_values('pa', ascending=False)
print(f'## {sym}（前半 {h1[0]}-{h1[1]} / 後半 {h2[0]}-{h2[1]}、コスト {c / 100:.3f}%）')
print('| 設定（H4_H1_きっかけ_方向） | 回数 | 前半 | 後半 | DD | 上位5回を除く |')
for x in T.itertuples():
    print(f'| {x.name} | {x.n} | {x.a:+.0f}R PF{x.pa:.2f} | {x.b:+.0f}R PF{x.pb:.2f} | {x.dd:.0f} | {x.ex5:+.0f}R |')
