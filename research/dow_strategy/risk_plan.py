"""How much risk per trade for a small start (user, 2026-10-24: ~300,000 JPY, thinking about ~1 %).
Adopted set incl. the right shoulder, calendar lots (gold Friday buys and month start 3 days x1.5).
Base risk 0.75 / 1.0 / 1.25 / 1.5 %, with and without the account rule 'risk halves while the account is >= 10 % below its
peak'. Two worlds: backtest as is, and a live haircut (every trade -0.1 R: slippage, swap, edge decay).
Month-block bootstrap: 10-year paths -> median CAGR, chance of DD beyond -20/-30/-40/-50 %;
1-year paths from 300,000 JPY -> median / 5 % worst balance, chance of ending the year below the start."""
import numpy as np, pandas as pd
src = open(__file__.replace('risk_plan.py', 'cal_size.py')).read().split("pd.set_option('display.width', 220)")[0]
ns = {'__file__': __file__}; exec(src, ns)
X, W = ns['X'], ns['W']
w1, w2 = W['1 金の金曜（金の買い）'], W['2 月初3日（全EA）']
X = X.copy(); X['mult'] = 1.0; X.loc[w1 | w2, 'mult'] = 1.5
ms = pd.period_range('2005-01', '2026-09', freq='M')
byM = {m: g.sort_values('et')[['R', 'mult']].to_numpy() for m, g in X.groupby(X.et.dt.to_period('M'))}
seqs = [byM.get(m, np.zeros((0, 2))) for m in ms]
rng = np.random.default_rng(7)
P10 = [np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 120)]) for _ in range(1000)]
P1 = [np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 12)]) for _ in range(3000)]


def sim(path, risk, rule, hair):
    eq = 1.0; peak = 1.0; mdd = 0.0
    for R, k in path:
        r = risk * k * (0.5 if rule and eq < 0.9 * peak else 1.0)
        eq *= 1 + r * (R - hair)
        if eq > peak: peak = eq
        d = eq / peak - 1
        if d < mdd: mdd = d
    return eq, mdd


rows = []
for hair, wn in ((0.0, 'バックテストどおり'), (0.1, '本番で1回-0.1R')):
    for risk in (0.0075, 0.01, 0.0125, 0.015):
        for rule in (False, True):
            r10 = np.array([sim(p, risk, rule, hair) for p in P10]); r1 = np.array([sim(p, risk, rule, hair)[0] for p in P1]) * 300000
            dd = r10[:, 1]
            rows.append({'想定': wn, '普段のリスク': f'{risk:.2%}（{risk * 300000:,.0f}円）', 'DD10%で半分': 'あり' if rule else 'なし',
                         '年利(中央)': f'{np.median(r10[:, 0]) ** 0.1 - 1:.0%}', 'DD中央': f'{np.median(dd):.0%}',
                         'DD-20%超': f'{(dd < -0.2).mean():.0%}', 'DD-30%超': f'{(dd < -0.3).mean():.0%}', 'DD-40%超': f'{(dd < -0.4).mean():.0%}', 'DD-50%超': f'{(dd < -0.5).mean():.0%}',
                         '1年後(中央)': f'{np.median(r1):,.0f}円', '1年後(悪い方5%)': f'{np.quantile(r1, 0.05):,.0f}円', '1年後に元本割れ': f'{(r1 < 300000).mean():.0%}'})
pd.set_option('display.width', 280)
print(pd.DataFrame(rows).to_string(index=False))
