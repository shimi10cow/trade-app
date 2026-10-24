import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.concat([pd.read_pickle(f'{S}/feat/pbstate_trades_{p}.pkl') for p in ('EURUSD', 'USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD')])
A['grp'] = np.where(A.pair.isin(['USDJPY', 'XAUUSD', 'BTCUSD']), 'トレンド型', '戻り型')
def lab(d, c): return '逆向き' if d < 0 else 'なし' if d == 0 else ('B〜1回目' if c == 0 else f'{min(c,4)}回目' + ('以降' if c >= 4 else '').replace('4回目以降', '4回目以降'))
for tf in ('H1', 'H4'):
    A[tf] = [lab(d, c) for d, c in zip(A[f'{tf}_dir'], A[f'{tf}_cnt'])]
order = ['B〜1回目', '1回目', '2回目', '3回目', '4回目以降', '逆向き', 'なし']
for tf in ('H1', 'H4'):
    print(f'\n### {tf} の状態別 平均R（前半/後半、回数）')
    for name, G in (('全部', A), ('採用中', A[A.adopted]), ('トレンド型', A[A.grp == 'トレンド型']), ('戻り型', A[A.grp == '戻り型'])):
        g = G.groupby([tf, 'half']).R.agg(['mean', 'size']).unstack('half')
        print(f'{name:6s} ' + ' | '.join(f"{k}: {g.loc[k,('mean',1)]:+.2f}/{g.loc[k,('mean',2)]:+.2f}（{int(g.loc[k,('size',1)])}/{int(g.loc[k,('size',2)])}）" for k in order if k in g.index))
A.to_pickle(f'{S}/feat/pbstate_all.pkl')
