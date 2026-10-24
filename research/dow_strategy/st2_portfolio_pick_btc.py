"""Pick the BTC trend EA (S) setting by its portfolio effect in BTC's own first half (2017-2021) only.
Portfolio = current 7 + gold L + gold S (ma_prov_buy_mt3_h1a1, picked on 2005-2015) + one BTC S setting.
Risk per trade fixed at the level picked for the portfolio without BTC (DD -20% on 2005-2015). Second half 2022-2026 = check."""
import pandas as pd, numpy as np
from multiprocessing import Pool
import st2_portfolio_pick as Q
P = Q.P
G = Q.load('S', 'XAUUSD', 'st2/S_ma_prov_buy_mt3_h1a1.csv')
B1 = pd.concat([Q.B0, G], ignore_index=True); B1['key'] = B1.ea + '@' + B1.pair
RISK = P.evaluate(B1, {k: 1.0 for k in B1.key.unique()})[0]
def one(f):
    T = pd.concat([B1, Q.load('S', 'BTCUSD', f)], ignore_index=True); T['key'] = T.ea + '@' + T.pair
    w = {k: 1.0 for k in T.key.unique()}
    a = P.simulate(T, w, RISK, 2017, 2021); b = P.simulate(T, w, RISK, 2022, 2026)
    return f, a[0], a[1], b[0], b[1], b[2]
if __name__ == '__main__':
    base_a = P.simulate(B1, {k: 1.0 for k in B1.key.unique()}, RISK, 2017, 2021); base_b = P.simulate(B1, {k: 1.0 for k in B1.key.unique()}, RISK, 2022, 2026)
    print(f'BTCなし（リスク{RISK:.2%}）: 2017-21 年{base_a[0]:.1%} DD{base_a[1]:.1%} | 2022-26 年{base_b[0]:.1%} DD{base_b[1]:.1%} 最悪年{base_b[2]:.1%}')
    fs = [f'st2/{p.name}' for p in sorted((P.RES / 'btcusd' / 'st2').glob('S_*.csv'))]
    with Pool(4) as p:
        R = pd.DataFrame(p.map(one, fs), columns=['f', 'a', 'add', 'b', 'bdd', 'worst'])
    R['score'] = R.a / -R['add']                    # first-half return per unit of drawdown
    R = R.sort_values('score', ascending=False); R.to_csv(P.RES / 'btcusd' / 'st2_portfolio_pick.csv', index=False)
    print(f'前半スコアと後半スコアの順位相関 {R.score.rank().corr((R.b / -R.bdd).rank()):.2f}')
    print('| BTC Sの設定 | 2017-21 年利 | DD | 2022-26 年利 | DD | 最悪年 |')
    for x in R.head(8).itertuples():
        print(f'| {x.f.split("/")[1][2:-4]} | {x.a:.1%} | {x.add:.1%} | {x.b:.1%} | {x.bdd:.1%} | {x.worst:.1%} |')
