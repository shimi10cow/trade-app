"""Throttle on the real sequence: risk chosen so that the FIRST half max DD = -20%, then the second half as a check.
Also the longest time below the previous high (months)."""
import numpy as np, pandas as pd
from pfx import BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_feat2.pkl'); X = A[A.key.isin(BASE9T2)].sort_values('et')
def sim(lo, hi, risk, D, mult):
    d = X[(X.et.dt.year >= lo) & (X.et.dt.year <= hi)]
    eq = 1.0; pk = 1.0; mdd = 0; pk_t = d.et.iat[0]; uw = pd.Timedelta(0); yr = {}
    for r, t in zip(d.R.to_numpy(), d.et):
        k = mult if eq < pk * (1 - D) else 1.0
        y0 = eq; eq *= 1 + risk * k * r
        yr[t.year] = yr.get(t.year, 1) * (eq / y0)
        if eq >= pk: pk = eq; pk_t = t
        else: uw = max(uw, t - pk_t)
        mdd = min(mdd, eq / pk - 1)
    return eq ** (1 / (hi - lo + 1)) - 1, mdd, min(yr.values()) - 1, uw.days / 30.4
for D, mult in ((1, 1), (0.10, 0.5), (0.15, 0.5), (0.10, 0.75), (0.05, 0.75)):
    a, b = 0.001, 0.05
    for _ in range(25):
        m = (a + b) / 2
        if sim(2005, 2015, m, D, mult)[1] < -0.20: b = m
        else: a = m
    f = sim(2005, 2015, a, D, mult); s = sim(2016, 2026, a, D, mult)
    lab = '基準' if D == 1 else f'DD{D:.0%}超でリスク×{mult}'
    print(f'{lab:20s} リスク{a:.2%} | 前半 年{f[0]:.1%} DD{f[1]:.1%} 最悪年{f[2]:.1%} 最長{f[3]:.0f}か月 | 後半 年{s[0]:.1%} DD{s[1]:.1%} 最悪年{s[2]:.1%} 最長{s[3]:.0f}か月')
