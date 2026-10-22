"""Is the drawdown throttle hindsight? (2026-10-22)
(1) trades fully shuffled (no losing streaks left in the data): does the throttle still help?
(2) compare at the SAME median growth (not the same DD): DD, time under water, chance of being down after 3 years."""
import numpy as np, pandas as pd
from pfx import BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_feat2.pkl'); X = A[A.key.isin(BASE9T2)].sort_values('et')
R = X.R.to_numpy(); per_yr = len(R) / 22; N = int(per_yr * 10); rng = np.random.default_rng(11)
iid = [rng.choice(R, N) for _ in range(1500)]
ms = pd.period_range('2005-01', '2026-09', freq='M'); byM = {k: g.R.to_numpy() for k, g in X.groupby(X.et.dt.to_period('M'))}
seqs = [byM.get(k, np.array([])) for k in ms]
blk = [np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 120)]) for _ in range(1500)]
def run(r, risk, D, m):
    eq = pk = 1.0; md = 0; uw = cur = 0; e3 = None; n3 = int(per_yr * 3)
    for j, x in enumerate(r):
        k = m if eq < pk * (1 - D) else 1.0; eq *= 1 + risk * k * x
        if eq >= pk: pk = eq; cur = 0
        else: cur += 1; uw = max(uw, cur)
        md = min(md, eq / pk - 1)
        if j == n3: e3 = eq
    return md, eq, uw / per_yr * 12, e3
def stats(P, risk, D, m):
    o = np.array([run(r, risk, D, m) for r in P])
    return dict(g=np.median(o[:, 1]) ** 0.1 - 1, dd=np.median(o[:, 0]), dd10=np.percentile(o[:, 0], 10), p30=(o[:, 0] < -0.3).mean(),
                uw=np.median(o[:, 2]), down3=(o[:, 3] < 1).mean())
for name, P in (('トレードを完全に混ぜた（連敗の偏りなし）', iid), ('月ごとに並べ替え', blk)):
    print(f'\n### {name}')
    base = stats(P, 0.0075, 1, 1)
    # throttle risk that gives the same median growth as the base
    a, b = 0.0075, 0.02
    for _ in range(14):
        mid = (a + b) / 2
        if stats(P, mid, 0.10, 0.5)['g'] < base['g']: a = mid
        else: b = mid
    th = stats(P, a, 0.10, 0.5)
    for lab, rk, s in (('固定 0.75%', 0.0075, base), (f'DD10%超で半分（ふだん {a:.2%}）', a, th)):
        print(f"{lab:26s} 年利{s['g']:.1%} DD中央{s['dd']:.0%} 悪い方10%{s['dd10']:.0%} -30%超{s['p30']:.0%} 最長の負け期間(中央){s['uw']:.0f}か月 3年後にマイナス{s['down3']:.0%}", flush=True)
