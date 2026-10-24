"""Right shoulder on US500, BUYS only (H1, stop above the left shoulder, 2R, pullback >= 4 ATR H4) added to the adopted set
incl. the gold / Nikkei right shoulder: same-risk comparison, fixed-risk DD and bootstrap (2026-10-24)."""
import numpy as np, pandas as pd, pfx, port_ds2 as P2, new_summary as N
CS = P2.CS; S = CS.S
X1 = P2.X1.copy(); keys = list(X1.key.unique())
f = f'{S}/ws_US500/research/dow_strategy/results/ds/DS_H1_left_tp2.csv'
x = N.load('US500', 'ds/DS_H1_left_tp2.csv').reset_index(drop=True)
d = pd.read_csv(f, usecols=['t', 'tag', 'side']).assign(t=lambda d: pd.to_datetime(d.t)).drop_duplicates('t')
d['dep'] = d.tag.str.split('|').str[2].astype(float)
x = x.merge(d[['t', 'dep']], left_on='tt', right_on='t', how='left')
U = x[(x.dep >= 4) & (x.side == 1)].assign(key='DS@US500', pair='US500')[['R', 'tt', 'et', 'key', 'pair']]
print('US500 右肩 買い', len(U), '回、合計', round(U.R.sum(), 1))
X2 = pd.concat([X1, U], ignore_index=True)
for X in (X1, X2): X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
pfx.ev(X1, keys, label='採用（右肩 金・日経込み）')
pfx.ev(X1, keys, U, label='＋US500 右肩（買いだけ）')
for nm, X in (('採用', X1), ('＋US500 右肩', X2)):
    c, dd, y, n = CS.fixed(X, 0.0075); med, tail = P2.boot_dd(X, 0.0075)
    print(f'{nm}: 0.75%固定 年利 {c:.1%} 最大DD {dd:.1%} 最悪年 {y.min():+.1%} 年{n:.0f}回 | DD中央 {med:.1%} 悪い方5% {tail:.1%}')
m0 = X1.groupby(X1.et.dt.to_period('M')).R.sum(); m1 = U.assign(et=pd.to_datetime(U.et)).groupby(pd.to_datetime(U.et).dt.to_period('M')).R.sum()
print('月ごとの相関', round(pd.concat([m0, m1], axis=1).fillna(0).corr().iloc[0, 1], 2))
