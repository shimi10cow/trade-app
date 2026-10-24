import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_mkt.pkl').join(pd.read_pickle(f'{S}/feat/cross_feat.pkl'))
A.to_pickle(f'{S}/feat/all_feat2.pkl')
def qb(g, f):
    cuts = g[g.half == 1][f].dropna().quantile([.2, .4, .6, .8]).to_numpy()
    b = pd.Series(np.searchsorted(cuts, g[f].to_numpy()), index=g.index).where(g[f].notna()); return b
for f in ('usd_cons', 'jpy_cons', 'stop_atr', 'rn_room'):
    G0 = A[A[f].notna()].copy(); G0['b'] = pd.concat([qb(g, f) for _, g in G0.groupby('pair')])
    print(f'\n### {f}  （5分位 0=小…4=大、平均R 前半/後半）')
    for name, G in (('全体', G0), ('採用', G0[G0.adopted])) + tuple((p, G0[G0.pair == p]) for p in sorted(G0.pair.unique())):
        m = G.groupby(['b', 'half']).R.mean().unstack()
        c = np.corrcoef(m[1], m[2])[0, 1] if len(m) == 5 else np.nan
        print(f'{name:8s} ' + ' '.join(f'{m.loc[i,1]:+.2f}/{m.loc[i,2]:+.2f}' for i in m.index) + f'  一致{c:+.2f}')
