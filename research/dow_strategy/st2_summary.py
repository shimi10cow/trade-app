"""Summarise the st2 grid: per-setting results (instrument split + cost), first-half ranking and, per option, how the
whole family behaves in the second half (to tell robust choices from lucky ones)."""
import sys, numpy as np, pandas as pd
from pathlib import Path
CFG = {'XAUUSD': ((2005, 2015), (2016, 2026), 2.5), 'BTCUSD': ((2017, 2021), (2022, 2026), 8.0)}
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
sym, D = sys.argv[1], Path(sys.argv[2]); h1, h2, c = CFG[sym]; rows = []
for f in sorted(D.glob('S_*.csv')):
    d = pd.read_csv(f, parse_dates=['t'])
    if not len(d): continue
    R = d.R - (c - 1.2) * 1e-4 / d.risk; y = d.t.dt.year; m = y >= h1[0]
    a = R[m & (y <= h1[1])]; b = R[(y >= h2[0]) & (y <= h2[1])]; allr = R[m]
    o = np.argsort(d.t[m].to_numpy()); eq = allr.to_numpy()[o].cumsum(); dd = (eq - np.maximum.accumulate(eq)).min()
    k = f.stem.split('_')[1:]
    rows.append(dict(name='_'.join(k), c4=k[0], c1=k[1], side=k[2] if k[2] != 'both' else 'both_d', stop=k[-2], exit=k[-1], n=len(allr),
                     a=a.sum(), pa=pf(a), b=b.sum(), pb=pf(b), dd=dd, ex5=allr.sum() - allr.nlargest(5).sum(),
                     wr=(allr > 0).mean()))
T = pd.DataFrame(rows); T.to_csv(D / f'summary_{sym}.csv', index=False)
print(f'## {sym}（前半 {h1[0]}-{h1[1]} / 後半 {h2[0]}-{h2[1]}、コスト {c / 100:.3f}%、{len(T)} 通り）')
print(f'前後半とも黒字: {((T.a > 0) & (T.b > 0)).mean():.0%}、後半黒字: {(T.b > 0).mean():.0%}、前半PF と 後半PF の順位相関: {T.pa.rank().corr(T.pb.rank()):.2f}')
print('\n選択肢ごと（その選択肢を含む全設定の中央値）')
for dim in ('c4', 'c1', 'side', 'stop', 'exit'):
    g = T.groupby(dim).agg(前半PF=('pa', 'median'), 後半PF=('pb', 'median'), 前半R=('a', 'median'), 後半R=('b', 'median'), DD=('dd', 'median'), 大勝ち除く=('ex5', 'median'))
    print(f'[{dim}]'); print(g.round(2).to_string())
print('\n前半の PF 上位 10（前半だけで選んだ場合）')
print('| 設定 | 回数 | 勝率 | 前半 | 後半 | DD | 上位5回を除く |')
for x in T.sort_values('pa', ascending=False).head(10).itertuples():
    print(f'| {x.name} | {x.n} | {x.wr:.0%} | {x.a:+.0f}R PF{x.pa:.2f} | {x.b:+.0f}R PF{x.pb:.2f} | {x.dd:.0f} | {x.ex5:+.0f}R |')
