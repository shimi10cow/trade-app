"""Pick Q settings for gold / USDJPY by FIRST-half portfolio gain only (small family), then check the second half."""
import glob, os, sys
import numpy as np, pandas as pd
import portfolio_opt as P
from pfx import ev, BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_feat2.pkl')
D = {'USDJPY': f'{S}/ws_USDJPY/research/dow_strategy/results/q', 'XAUUSD': f'{S}/ws_XAUUSD/research/dow_strategy/results/q'}
COST = {'XAUUSD': 2.5}
def load(p, f):
    x = pd.read_csv(f); x['tt'] = pd.to_datetime(x.t); x['et'] = pd.to_datetime(x.exit_t)
    x['R'] = x.R - (COST.get(p, 1.2) - 1.2) * 1e-4 / x.risk; x = x[(x.tt.dt.year >= 2005)]
    x['key'] = f'Q{os.path.basename(f)[1:-4]}@{p}'; x['pair'] = p; return x[['R', 'tt', 'et', 'key', 'pair']]
base = A[A.key.isin(BASE9T2)][['R', 'tt', 'et', 'key', 'pair']]
r0, a0, b0 = P.evaluate(base, {k: 1 for k in base.key.unique()})
best = {}
for p, d in D.items():
    rows = []
    for f in sorted(glob.glob(f'{d}/Q_*.csv')):
        x = load(p, f)
        if (x.tt.dt.year <= 2015).sum() < 40: continue
        X = pd.concat([base, x]); r, a, b = P.evaluate(X, {k: 1 for k in X.key.unique()})
        rows.append((x.key.iat[0], a[0] - a0[0], b[0] - b0[0], b[1] - b0[1]))
    R = pd.DataFrame(rows, columns=['key', 'dA', 'dB', 'dDD']).sort_values('dA', ascending=False)
    print(f'\n== {p}（前半の改善で並べた上位10、全{len(R)}設定）。前半の改善と後半の改善の順位相関 {R.dA.rank().corr(R.dB.rank()):+.2f}')
    print(R.head(10).round(3).to_string(index=False))
    best[p] = load(p, f"{d}/Q_{R.key.iat[0].split('@')[0][2:]}.csv")
print()
ev(A, BASE9T2, label='9本T2（基準）')
for p, x in best.items(): ev(A, BASE9T2, x, label=f'+ {x.key.iat[0]}')
ev(A, BASE9T2, pd.concat(best.values()), label='+ 両方')
pd.concat(best.values()).to_pickle(f'{S}/feat/q_best.pkl')
