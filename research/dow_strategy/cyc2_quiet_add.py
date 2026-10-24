"""New candidates: each EA on each instrument, only entries in a quiet market (vol_h1 below the pair's first-half 20%/40% cut).
Select on the first half only (PF>=1.2 and n>=25 and first-half portfolio gain), then show second half."""
import numpy as np, pandas as pd
import portfolio_opt as P
from pfx import ev, BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_mkt.pkl')
cuts = {p: g[g.half == 1].vol_h1.quantile([.2, .4]).to_numpy() for p, g in A.groupby('pair')}
def pf(r): return r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
base = A[A.key.isin(BASE9T2)]
r0, a0, b0 = P.evaluate(base[['R', 'tt', 'et', 'key', 'pair']], {k: 1 for k in BASE9T2})
rows = []
for k, g in A.groupby('key'):
    if k in BASE9T2: continue
    p = g.pair.iat[0]
    for qi, ql in ((0, 'q20'), (1, 'q40')):
        x = g[g.vol_h1 < cuts[p][qi]].copy(); x['key'] = f'{k}:{ql}'
        h1 = x[x.half == 1].R; h2 = x[x.half == 2].R
        if len(h1) < 25: continue
        X = pd.concat([base, x])[['R', 'tt', 'et', 'key', 'pair']]
        r, a, b = P.evaluate(X, {kk: 1 for kk in X.key.unique()})
        rows.append((f'{k}:{ql}', len(h1), h1.sum(), pf(h1), len(h2), h2.sum(), pf(h2), a[0] - a0[0], b[0] - b0[0], b[1] - b0[1]))
R = pd.DataFrame(rows, columns=['key', 'n1', 'R1', 'PF1', 'n2', 'R2', 'PF2', 'dA', 'dB', 'dDD']).sort_values('dA', ascending=False)
print(R.round(3).to_string(index=False))
sel = R[(R.PF1 >= 1.2) & (R.dA > 0.005)]
print('\n前半で選ばれた', len(sel), '本：後半 PF>1 は', (sel.PF2 > 1).sum(), '本、後半年利の変化の平均', round(sel.dB.mean(), 4))
R.to_csv(f'{S}/feat/quiet_add.csv', index=False)
