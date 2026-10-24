import glob, os
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
D = {'EURUSD': 'results/pb2'} | {p: f'{S}/ws_{p}/research/dow_strategy/results/pb2' for p in ('USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD')}
COST = {'XAUUSD': 2.5, 'BTCUSD': 8.0}; SPLIT = {'BTCUSD': ((2017, 2021), (2022, 2026))}
def pf(r): return r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
rows = []
for p, d in D.items():
    for f in glob.glob(f'{d}/PB2_*.csv'):
        x = pd.read_csv(f)
        if not len(x): continue
        x['t'] = pd.to_datetime(x.t); R = x.R - (COST.get(p, 1.2) - 1.2) * 1e-4 / x.risk
        (a0, a1), (b0, b1) = SPLIT.get(p, ((2005, 2015), (2016, 2026))); y = x.t.dt.year
        r1 = R[(y >= a0) & (y <= a1)]; r2 = R[(y >= b0) & (y <= b1)]
        rows.append((p, os.path.basename(f)[4:-4], len(r1), r1.sum(), pf(r1), len(r2), r2.sum(), pf(r2), R.nlargest(5).sum()))
Q = pd.DataFrame(rows, columns=['pair', 'cfg', 'n1', 'R1', 'PF1', 'n2', 'R2', 'PF2', 'top5'])
Q.to_csv(f'{S}/feat/pb2_summary.csv', index=False)
for p, g in Q.groupby('pair'):
    print(f'\n== {p}: 前半 PF>1.15 の設定 {(g.PF1>1.15).sum()}/{len(g)}、そのうち後半 PF>1 {((g.PF1>1.15)&(g.PF2>1)).sum()}、前後半 PF の相関 {np.corrcoef(g.PF1,g.PF2)[0,1]:+.2f}')
    print(g.sort_values('PF1', ascending=False).head(8).round(2).to_string(index=False))
# parameter-level averages over all pairs
Q[['ks', 'h4', 'trig', 'stop', 'ex']] = Q.cfg.str.split('_', expand=True)
for c in ('ks', 'h4', 'trig', 'stop'):
    print('\n', c); print(Q.groupby(['pair', c])[['PF1', 'PF2']].mean().unstack(c).round(2).to_string())
