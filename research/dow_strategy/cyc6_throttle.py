"""Cut risk while in a drawdown (2026-10-22). Rule: risk x m when equity is more than D below its high. Compared at the same
chance of a -30% DD (month-block bootstrap of 10-year paths, second half only and all years)."""
import numpy as np, pandas as pd
from pfx import BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_feat2.pkl'); X = A[A.key.isin(BASE9T2)]
def paths(lo, hi, n=1500, seed=3):
    Y = X[(X.et.dt.year >= lo) & (X.et.dt.year <= hi)]
    ms = pd.period_range(f'{lo}-01', '2026-09', freq='M')
    byM = {m: g.sort_values('et').R.to_numpy() for m, g in Y.groupby(Y.et.dt.to_period('M'))}
    seqs = [byM.get(m, np.array([])) for m in ms]; rng = np.random.default_rng(seed)
    return [np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 120)]) for _ in range(n)]
def run(r, risk, D, mult):
    eq = 1.0; pk = 1.0; mdd = 0.0
    for x in r:
        k = mult if eq < pk * (1 - D) else 1.0
        eq *= 1 + risk * k * x; pk = max(pk, eq); mdd = min(mdd, eq / pk - 1)
    return mdd, eq
def same_risk(P, D, mult):
    def stat(risk):
        o = [run(r, risk, D, mult) for r in P]; dd = np.array([a for a, _ in o]); fin = np.array([b for _, b in o])
        return (dd < -0.30).mean(), np.median(fin) ** 0.1 - 1, np.median(dd)
    a, b = 0.001, 0.03
    for _ in range(14):
        m = (a + b) / 2
        if stat(m)[0] > 0.05: b = m
        else: a = m
    return a, stat(a)
if __name__ == "__main__":
  P2 = paths(2016, 2026); PA = paths(2005, 2026)
  for D, mult in ((1, 1.0), (0.10, 0.5), (0.15, 0.5), (0.10, 0.75), (0.20, 0.5), (0.05, 0.75)):
      r2, s2 = same_risk(P2, D, mult); ra, sa = same_risk(PA, D, mult)
      lab = '基準（そのまま）' if D == 1 else f'DD{D:.0%}超でリスク×{mult}'
      print(f'{lab:22s} 後半だけ 年{s2[1]:.1%}（リスク{r2:.2%}、DD中央{s2[2]:.0%}） 全期間 年{sa[1]:.1%}（リスク{ra:.2%}、DD中央{sa[2]:.0%}）', flush=True)
