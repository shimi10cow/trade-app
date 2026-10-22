"""Pick the gold trend EA (S) setting by its effect on the WHOLE portfolio in the first half only (2005-2015):
current 7 EAs + gold L + one S setting, equal weights, risk scaled to first-half DD -20%; rank by first-half CAGR.
Second half shown for checking only."""
import sys, pandas as pd, numpy as np
from multiprocessing import Pool
import portfolio_opt as P
P.DIRS['XAUUSD'] = P.RES / 'xauusd'; P.DIRS['BTCUSD'] = P.RES / 'btcusd'
COST = {'XAUUSD': 2.5, 'BTCUSD': 8.0}
def load(ea, pair, f):
    x = P.load(ea, pair, f)
    if pair in COST:
        d = pd.read_csv(P.DIRS[pair] / f); t = pd.to_datetime(d.time if 'time' in d else d.t); risk = d.risk.to_numpy()[t.dt.year >= 2005]
        x['R'] = x.R.to_numpy() - (COST[pair] - 1.2) * 1e-4 / risk
    return x
BASE = [['R', 'EURUSD', 'regime2_R2c.csv'], ['T', 'EURUSD', 'regime2_T1t.csv'], ['L', 'EURUSD', 'tl_N2.csv'], ['A', 'EURUSD', 'retest_N1.csv'],
        ['C', 'EURUSD', 'step2/cl15_md4tri.csv'], ['C', 'USDJPY', 'step2/cl15_md4tri.csv'], ['J2', 'USDJPY', 'turn/jt2_h1major+hour0_10.csv'], ['L', 'XAUUSD', 'tl_N2.csv']]
B0 = pd.concat([load(*it) for it in BASE], ignore_index=True)
def one(f):
    T = pd.concat([B0, load('S', 'XAUUSD', f)], ignore_index=True); T['key'] = T.ea + '@' + T.pair
    w = {k: 1.0 for k in T.key.unique()}; r, a, b = P.evaluate(T, w)
    return f, r, a[0], b[0], b[1], b[2]
if __name__ == '__main__':
    fs = [f'st2/{p.name}' for p in sorted((P.RES / 'xauusd' / 'st2').glob('S_*.csv'))] + ['st/S_ma_prov_dow_buy.csv']
    with Pool(4) as p:
        R = pd.DataFrame(p.map(one, fs), columns=['f', 'risk', 'a', 'b', 'dd', 'worst'])
    R = R.sort_values('a', ascending=False); R.to_csv(P.RES / 'xauusd' / 'st2_portfolio_pick.csv', index=False)
    print(f'前半の全体年利と後半の全体年利の順位相関 {R.a.rank().corr(R.b.rank()):.2f}')
    print('| ゴールドSの設定 | リスク/回 | 前半 全体年利 | 後半 全体年利 | 後半DD | 後半最悪年 |')
    for x in R.head(10).itertuples():
        print(f'| {x.f.split("/")[1][2:-4]} | {x.risk:.2%} | {x.a:.1%} | {x.b:.1%} | {x.dd:.1%} | {x.worst:.1%} |')
    print('中央値', f"前半 {R.a.median():.1%} 後半 {R.b.median():.1%}")
