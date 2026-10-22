import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
T = pd.read_pickle(f'{S}/feat/all_trades_hold.pkl')
D = pd.concat([pd.read_pickle(f'{S}/feat/exit_time_{p}.pkl') for p in T.pair.unique()])
A = T.join(D); A.to_pickle(f'{S}/feat/all_exit_time.pkl')
A['grp'] = np.where(A.pair.isin(['USDJPY', 'XAUUSD', 'BTCUSD']), 'trend', 'mr')
V = [c for c in D.columns]
print('変化（合計R、前半/後半）と 前後半とも改善したEA数 / 56')
for v in V:
    d = A[v] - A.R
    g = d.groupby([A.key, A.half]).sum().unstack()
    both = ((g[1] > 0) & (g[2] > 0)).sum(); worse = ((g[1] < 0) & (g[2] < 0)).sum()
    gt = d.groupby([A.grp, A.half]).sum().unstack()
    ad = d[A.adopted].groupby(A.half).sum()
    print(f'{v:10s} 全 {g[1].sum():+7.1f}/{g[2].sum():+7.1f} 改善{both:2d} 悪化{worse:2d} | トレンド型 {gt.loc["trend",1]:+6.1f}/{gt.loc["trend",2]:+6.1f} 戻り型 {gt.loc["mr",1]:+6.1f}/{gt.loc["mr",2]:+6.1f} | 採用 {ad[1]:+6.1f}/{ad[2]:+6.1f}')
