"""Combos of the stable instruments only (XM costs). Per pattern: halves (first-half DD -20%), same-risk bootstrap,
and a fixed 0.5 % risk per trade over 2005-2026 (CAGR, max DD, worst year, trades/year, yearly returns)."""
import numpy as np, pandas as pd, pfx
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl'); A = pd.read_pickle(f'{S}/feat/all_trades_new.pkl')
Q = pd.read_pickle(f'{S}/feat/q_best.pkl').copy(); Q['key'] = 'Q@' + Q.pair
cols = ['R', 'tt', 'et', 'key', 'pair']
POOL = pd.concat([T[cols], A[~A.pair.isin(T.pair.unique())][cols], Q[~Q.key.isin(T.key)][cols]], ignore_index=True)
HALF = {'S@XAUUSD': 0.5, 'Q@XAUUSD': 0.5}
B = pfx.BASE9T2
P = {'① 今の9本（ユーロドル・ドル円・ゴールド）': B,
     '② ①＋ゴールドQ（S/Q半分ずつ）': B + ['Q@XAUUSD'],
     '③ ②＋銀Q': B + ['Q@XAUUSD', 'Q@XAGUSD'],
     '④ ③＋US30（T・Q）': B + ['Q@XAUUSD', 'Q@XAGUSD', 'T@US30', 'Q@US30'],
     '⑤ ④＋ドル円Q': B + ['Q@XAUUSD', 'Q@XAGUSD', 'T@US30', 'Q@US30', 'Q@USDJPY'],
     '⑥ ⑤＋円クロス（CADJPY PB2・AUDJPY J3・GBPJPY J3）': B + ['Q@XAUUSD', 'Q@XAGUSD', 'T@US30', 'Q@US30', 'Q@USDJPY', 'PB2@CADJPY', 'J3@AUDJPY', 'J3@GBPJPY'],
     '⑦ 各銘柄の一番だけ（ユーロドルT2・ドル円J2・ゴールドL2・銀Q・US30T）': ['T2@EURUSD', 'J2@USDJPY', 'L2@XAUUSD', 'Q@XAGUSD', 'T@US30'],
     '参考 ⑤＋BTC（A・J2）': B + ['Q@XAUUSD', 'Q@XAGUSD', 'T@US30', 'Q@US30', 'Q@USDJPY', 'A@BTCUSD', 'J2@BTCUSD']}
def mk(keys):
    X = POOL[POOL.key.isin(keys)].copy()
    if 'Q@XAUUSD' in keys:
        for k, w in HALF.items(): X.loc[X.key == k, 'R'] *= w
    return X
def fixed(X, risk=0.005):
    d = X.sort_values('et'); r = d.R.to_numpy() * risk; eq = np.cumprod(1 + r); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    y = pd.Series(r).groupby(d.et.dt.year.to_numpy()).apply(lambda g: np.prod(1 + g) - 1)
    yrs = 2026 - 2005 + 0.8
    return eq[-1] ** (1 / yrs) - 1, dd, y, len(d) / yrs
Y = {}
for lab, keys in P.items():
    X = mk(keys); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
    print(f'\n### {lab}（{len(keys)}本）', flush=True)
    pfx.ev(X, keys, label='  前後半/同じ危険度')
    c, dd, y, n = fixed(X); Y[lab[:2]] = y
    print(f'  1回0.5%固定 2005-26：年利 {c:.1%}  最大DD {dd:.1%}  最悪年 {y.min():.1%}({y.idxmin()})  マイナス年 {(y<0).sum()}/{len(y)}  年 {n:.0f} 回', flush=True)
print('\n### 年ごと（1回0.5%固定）'); print((pd.DataFrame(Y) * 100).round(1).to_string())
