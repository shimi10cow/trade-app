"""Small live account (2026-10-24): which adopted EAs fit an account of a given size, and how that subset performs.
An EA fits when its median minimum-lot risk (RESEARCH_LOG §102/§103/§104, XM KIWAMI, current prices) is <= 1% of the account.
Per subset: 1% risk with calendar multipliers and the 'half risk while >=10% below peak' rule, the five-period check and halves."""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
X = pd.read_pickle(f'{S}/feat/final_trades.pkl'); X['et'] = pd.to_datetime(X.et)
NEED = {'J2@USDJPY': 7.4e4, 'C@USDJPY': 7.4e4, 'R@EURUSD': 7.4e4, 'T2@EURUSD': 7.4e4, 'L@EURUSD': 7.4e4, 'A@EURUSD': 7.4e4, 'C@EURUSD': 7.4e4,
        'DS@JP225': 1.5e4, 'S@BTCUSD': 19.4e4, 'DS@US500': 24.4e4, 'M@US500': 32.6e4, 'T@US30': 39e4, 'L2@XAUUSD': 49.2e4,
        'DS@XAUUSD': 54.4e4, 'Q@XAGUSD': 56.7e4, 'Q@US30': 57.9e4, 'S@XAUUSD': 79.6e4, 'Q@XAUUSD': 86.4e4, 'M@US30': 207.6e4}
miss = sorted(set(X.key) - set(NEED)); assert not miss, miss
def sim(d, risk=0.01):
    d = d.sort_values('et'); eq = pk = 1.0; mdd = 0.0; out = []
    for R, k in zip(d.R.to_numpy() * d.wt.to_numpy(), d.mult.to_numpy()):
        eq *= 1 + risk * k * (0.5 if eq < 0.9 * pk else 1.0) * R; pk = max(pk, eq); mdd = min(mdd, eq / pk - 1); out.append(eq)
    yrs = (d.et.max() - d.et.min()).days / 365.25
    return eq ** (1 / yrs) - 1, mdd, len(d) / yrs
rows = []
for cap in (20e4, 30e4, 50e4, 60e4, 100e4, 300e4):
    ks = [k for k, v in NEED.items() if v <= cap]; d = X[X.key.isin(ks)]
    c, dd, n = sim(d)
    per = [sim(d[(d.et.dt.year >= a) & (d.et.dt.year <= b)])[0] for a, b in ((2005, 2009), (2010, 2013), (2014, 2017), (2018, 2021), (2022, 2026))]
    rows.append({'口座': f'{cap/1e4:.0f}万円', 'EA数': len(ks), '年利': f'{c:.0%}', '最大DD': f'{dd:.0%}', '年回数': round(n),
                 '5期間の年利': ' / '.join(f'{p:.0%}' for p in per), '後半R': round((d[d.half == 2].R * d[d.half == 2].wt).sum()),
                 '足すEA': ', '.join(k for k in ks if NEED[k] > (rows and float(rows[-1]['口座'][:-2]) * 1e4 or 0))})
pd.set_option('display.width', 250); print(pd.DataFrame(rows).to_string(index=False))
