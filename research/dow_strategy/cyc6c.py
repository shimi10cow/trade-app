import numpy as np, pandas as pd
from pfx import BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_feat2.pkl'); X = A[A.key.isin(BASE9T2)].sort_values('et')
def sim(lo, hi, risk, steps):
    d = X[(X.et.dt.year >= lo) & (X.et.dt.year <= hi)]
    eq = pk = 1.0; mdd = 0; pk_t = d.et.iat[0]; uw = pd.Timedelta(0); yr = {}
    for r, t in zip(d.R.to_numpy(), d.et):
        dd = 1 - eq / pk; k = 1.0
        for D, m in steps:
            if dd > D: k = m
        y0 = eq; eq *= 1 + risk * k * r; yr[t.year] = yr.get(t.year, 1) * (eq / y0)
        if eq >= pk: pk = eq; pk_t = t
        else: uw = max(uw, t - pk_t)
        mdd = min(mdd, eq / pk - 1)
    return eq ** (1 / (hi - lo + 1)) - 1, mdd, min(yr.values()) - 1, uw.days / 30.4
V = {'基準': [], '10%→0.5': [(0.10, 0.5)], '8%→0.5': [(0.08, 0.5)], '12%→0.5': [(0.12, 0.5)], '10%→0.5,18%→0.25': [(0.10, 0.5), (0.18, 0.25)],
     '6%→0.75,12%→0.5': [(0.06, 0.75), (0.12, 0.5)], '10%→0.33': [(0.10, 0.33)], '5%→0.5': [(0.05, 0.5)]}
for lab, st in V.items():
    a, b = 0.001, 0.05
    for _ in range(25):
        m = (a + b) / 2
        if sim(2005, 2015, m, st)[1] < -0.20: b = m
        else: a = m
    f = sim(2005, 2015, a, st); s = sim(2016, 2026, a, st)
    print(f'{lab:20s} リスク{a:.2%} | 前半 年{f[0]:.1%} 最悪年{f[2]:.1%} 最長{f[3]:.0f}か月 | 後半 年{s[0]:.1%} DD{s[1]:.1%} 最悪年{s[2]:.1%} 最長{s[3]:.0f}か月', flush=True)
