"""Which market conditions change the average R? Quintiles cut on each pair's first half; mean R per bucket per half."""
import sys
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
T = pd.read_pickle(f'{S}/feat/all_trades_hold.pkl')
F = pd.concat([pd.read_pickle(f'{S}/feat/mkt_{p}.pkl') for p in T.pair.unique()])
A = T.join(F); A.to_pickle(f'{S}/feat/all_mkt.pkl')
A['grp'] = np.where(A.pair.isin(['USDJPY', 'XAUUSD', 'BTCUSD']), 'trend', 'mr')
FE = ['vol_h1', 'vol_d1', 'd1_gap', 'd1_slope', 'rng20', 'room_pd', 'er24', 'dir24']
def qb(g, f):
    cuts = g[g.half == 1][f].quantile([.2, .4, .6, .8]).to_numpy()
    return pd.Series(np.searchsorted(cuts, g[f].to_numpy()), index=g.index)
for f in FE:
    A['b'] = pd.concat([qb(g, f) for _, g in A.groupby('pair')])
    print(f'\n### {f}  （5分位：0=小 … 4=大、平均R 前半/後半）')
    rows = []
    for name, G in (('全体', A), ('トレンド型', A[A.grp == 'trend']), ('戻り型', A[A.grp == 'mr']), ('採用', A[A.adopted])) + tuple((p, A[A.pair == p]) for p in sorted(A.pair.unique())):
        m = G.groupby(['b', 'half']).R.mean().unstack()
        c = np.corrcoef(m[1], m[2])[0, 1] if len(m) == 5 else np.nan
        rows.append(f'{name:8s} ' + ' '.join(f'{m.loc[i,1]:+.2f}/{m.loc[i,2]:+.2f}' for i in m.index) + f'  一致{c:+.2f}')
    print('\n'.join(rows))
for f, lab in (('d1_200', 'SMA200の向き'), ('wday', '曜日')):
    print(f'\n### {lab}'); print(A.groupby(['grp', f, 'half']).R.mean().unstack(['half']).unstack('grp').round(2).to_string())
A['hb'] = A.hour // 4
print('\n### 時間帯(ブローカー時間4時間ごと)'); print(A.groupby(['pair', 'hb', 'half']).R.mean().unstack(['pair', 'half']).round(2).to_string())
