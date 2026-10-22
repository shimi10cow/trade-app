"""Portfolio check helper on the master table: base set + candidates.
 (1) halves: risk scaled so first-half DD = -20%, equal weights (portfolio_opt.evaluate)
 (2) same-risk comparison: month-block bootstrap of 10-year paths from the SECOND half only (2016-2026) and from all years;
     find the risk at which the chance of a DD beyond -30% is 5%, report the median yearly growth at that risk."""
import numpy as np, pandas as pd
import portfolio_opt as P
BASE9 = ['R@EURUSD', 'T@EURUSD', 'L@EURUSD', 'A@EURUSD', 'C@EURUSD', 'C@USDJPY', 'J2@USDJPY', 'L2@XAUUSD', 'S@XAUUSD']
BASE9T2 = [k if k != 'T@EURUSD' else 'T2@EURUSD' for k in BASE9]
def boot(X, lo, hi, n=1500, seed=3):
    X = X[(X.et.dt.year >= lo) & (X.et.dt.year <= hi)]
    ms = pd.period_range(f'{lo}-01', f'{hi}-09' if hi == 2026 else f'{hi}-12', freq='M')
    byM = {m: g.sort_values('et').R.to_numpy() for m, g in X.groupby(X.et.dt.to_period('M'))}
    seqs = [byM.get(m, np.array([])) for m in ms]
    rng = np.random.default_rng(seed); paths = [np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 120)]) for _ in range(n)]
    def stat(risk):
        dd = []; fin = []
        for r in paths:
            eq = np.cumprod(1 + risk * r); dd.append((eq / np.maximum.accumulate(eq) - 1).min()); fin.append(eq[-1])
        return (np.array(dd) < -0.30).mean(), np.median(fin) ** 0.1 - 1, np.median(dd)
    a, b = 0.0005, 0.04
    for _ in range(18):
        m = (a + b) / 2
        if stat(m)[0] > 0.05: b = m
        else: a = m
    p, g, d = stat(a); return a, g, d
def ev(T, keys, extra=None, label='', bs=True):
    X = T[T.key.isin(keys)][['R', 'tt', 'et', 'key', 'pair']]
    if extra is not None: X = pd.concat([X, extra[['R', 'tt', 'et', 'key', 'pair']]], ignore_index=True)
    r, a, b = P.evaluate(X, {k: 1.0 for k in X.key.unique()})
    s = f'{label:34s} 前半 年{a[0]:5.1%} | 後半 年{b[0]:5.1%} DD{b[1]:6.1%} 最悪{b[2]:5.1%} 年÷DD{b[0]/-b[1]:.2f}'
    if bs:
        r2, g2, d2 = boot(X, 2016, 2026); r3, g3, d3 = boot(X, 2005, 2026)
        s += f' || 同じ危険度(-30%超5%)：後半だけ 年{g2:5.1%}(リスク{r2:.2%}) 全期間 年{g3:5.1%}(リスク{r3:.2%})'
    print(s, flush=True); return a, b
