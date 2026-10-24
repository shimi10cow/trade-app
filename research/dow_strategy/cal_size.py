"""Calendar windows as RISK adjustments on the adopted EAs (user, 2026-10-24: no chart-free trades; instead, when an EA
enters inside a favourable window, raise its lot). Windows (broker date of the entry):
  1 gold Friday    : gold EA BUYS entered on a Friday
  2 month start    : any adopted EA trade entered in the first 3 trading days of the month
  3 index Monday   : US30 / US500 / JP225 EA BUYS entered on a Monday
  4 turn of month  : gold / US500 EA BUYS entered from 3 trading days before the month end to the 3rd trading day
Step 1: mean R inside vs outside the window, by half (the evidence). Step 2: x1.25 / 1.5 / 2 inside the window,
same-risk comparison (pfx.ev) and fixed 0.75 % risk (CAGR, max DD, worst year)."""
import numpy as np, pandas as pd, pfx, port_ds2 as P2
CS = P2.CS; S = CS.S
A = pd.read_pickle(f'{S}/feat/cal_daily.pkl')
X = P2.X1.copy().reset_index(drop=True); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
T = pd.read_pickle(f'{S}/feat/late_eval.pkl')[['key', 'tt', 'side']].drop_duplicates(['key', 'tt'])
X = X.merge(T, on=['key', 'tt'], how='left')
# right shoulder side from its own files
for sym in ('XAUUSD', 'JP225'):
    d = pd.read_csv(f'{S}/ws_{sym}/research/dow_strategy/results/ds/DS_H1_left_tp2.csv', usecols=['t', 'side']).assign(tt=lambda d: pd.to_datetime(d.t)).drop_duplicates('tt')
    m = X.key == f'DS@{sym}'; X.loc[m, 'side'] = X.loc[m, 'tt'].map(d.set_index('tt').side).to_numpy()
for sym in ('US30', 'US500'):
    X.loc[X.key == f'M@{sym}', 'side'] = 1
X['side'] = X.side.fillna(0)
X['half'] = [1 if t.year <= {'US30': 2020, 'US500': 2021, 'JP225': 2021}.get(p, 2015) else 2 for t, p in zip(X.tt, X.pair)]
wd = X.tt.dt.dayofweek.to_numpy()
pos = np.zeros(len(X), int); neg = np.zeros(len(X), int)
for sym, g in X.groupby('pair'):
    D = A[A.sym == sym] if sym in set(A.sym) else A[A.sym == 'EURUSD']
    k = np.clip(D.index.searchsorted(g.tt.dt.normalize()), 0, len(D) - 1)
    pos[g.index] = D.pos.to_numpy()[k]; neg[g.index] = D.neg.to_numpy()[k]
gold, idx = (X.pair == 'XAUUSD').to_numpy(), X.pair.isin(['US30', 'US500', 'JP225']).to_numpy(); buy = (X.side == 1).to_numpy()
W = {'1 金の金曜（金の買い）': gold & buy & (wd == 4),
     '2 月初3日（全EA）': pos <= 3,
     '3 指数の月曜（指数の買い）': idx & buy & (wd == 0),
     '4 月末月初（金・US500 の買い）': (gold | (X.pair == 'US500').to_numpy()) & buy & ((neg <= 3) | (pos <= 3))}
pd.set_option('display.width', 220)
print('== 1. 期間の中と外（平均R、回数）')
for nm, w in W.items():
    rel = gold if nm.startswith('1') else idx if nm.startswith('3') else (gold | (X.pair == 'US500').to_numpy()) if nm.startswith('4') else np.ones(len(X), bool)
    rel = rel & (buy if not nm.startswith('2') else True)
    s = []
    for h in (1, 2):
        hh = (X.half == h).to_numpy()
        a = X.R[w & hh]; b = X.R[rel & ~w & hh]
        s.append(f'{"前半" if h == 1 else "後半"} 中 {a.mean():+.2f}R（{len(a)}回）／外 {b.mean():+.2f}R（{len(b)}回）')
    top = X.R[w].nlargest(5).sum() / X.R[w].sum() if X.R[w].sum() > 0 else np.nan
    print(f'{nm}: ' + ' | '.join(s) + f' | 中の上位5回の割合 {top:.0%}')
keys = list(X.key.unique())
print('\n== 2. 期間の中だけロットを上げる')
pfx.ev(X, keys, label='基準（採用・右肩込み）')
base_fix = CS.fixed(X, 0.0075)
print(f'   0.75%固定 年利 {base_fix[0]:.1%} 最大DD {base_fix[1]:.1%} 最悪年 {base_fix[2].min():.1%}')
for nm, w in W.items():
    for k in (1.25, 1.5, 2.0):
        Y = X.copy(); Y.loc[w, 'R'] *= k
        pfx.ev(Y, keys, label=f'{nm} ×{k}')
        c, dd, y, n = CS.fixed(Y, 0.0075)
        print(f'   0.75%固定 年利 {c:.1%} 最大DD {dd:.1%} 最悪年 {y.min():.1%}')
Y = X.copy()
for nm in ('1 金の金曜（金の買い）', '2 月初3日（全EA）'):
    Y.loc[W[nm], 'R'] *= 1.5
pfx.ev(Y, keys, label='1＋2 を ×1.5')
c, dd, y, n = CS.fixed(Y, 0.0075); print(f'   0.75%固定 年利 {c:.1%} 最大DD {dd:.1%} 最悪年 {y.min():.1%}')
