"""How deep can the drawdown get by luck? Month-block bootstrap of the candidate portfolio (current 7 + gold L + gold S).
Months of 2005-2026 trade returns are resampled with replacement into 10-year paths (5,000 paths) at a given risk per trade.
Reports the distribution of the 10-year max drawdown, the longest time below the high, and the final multiple."""
import numpy as np, pandas as pd
import portfolio_greedy as G
P = G.P
T = pd.concat([G.load(*b) for b in G.BASE], ignore_index=True)
T['m'] = T.et.dt.to_period('M')
rng = np.random.default_rng(7)
months = pd.period_range('2005-01', '2026-09', freq='M')
byM = {m: g.sort_values('et').R.to_numpy() for m, g in T.groupby('m')}
seqs = [byM.get(m, np.array([])) for m in months]
for risk in (0.005, 0.0085, 0.01):
    dd, uw, fin = [], [], []
    for _ in range(5000):
        idx = rng.integers(0, len(seqs), 120)
        r = np.concatenate([seqs[i] for i in idx]); mlen = np.array([len(seqs[i]) for i in idx])
        eq = np.cumprod(1 + risk * r); pk = np.maximum.accumulate(eq)
        dd.append((eq / pk - 1).min()); fin.append(eq[-1])
        # longest underwater in months
        mend = np.cumsum(mlen) - 1; mend = mend[mend >= 0]
        e_m = eq[mend[mlen > 0]] if len(mend) else eq[-1:]
        pkm = np.maximum.accumulate(e_m); under = e_m < pkm; best = cur = 0
        for u in under:
            cur = cur + 1 if u else 0; best = max(best, cur)
        uw.append(best)
    dd, uw, fin = np.array(dd), np.array(uw), np.array(fin)
    q = lambda a, p: np.percentile(a, p)
    print(f'リスク{risk:.2%}: 10年の最大DD 中央{q(dd,50):.0%} 悪い方10%{q(dd,10):.0%} 悪い方1%{q(dd,1):.0%} | -30%を超える確率 {(dd<-0.30).mean():.0%} | '
          f'最長マイナス期間 中央{q(uw,50):.0f}か月 悪い方10%{q(uw,90):.0f}か月 | 10年後の倍率 中央{q(fin,50):.1f}倍 悪い方10%{q(fin,10):.1f}倍', flush=True)
