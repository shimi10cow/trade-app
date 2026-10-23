"""Apply each view proxy as 'skip trades against it' to the gold EAs (20 years). Choice on the first half."""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
X = pd.read_pickle(f'{S}/feat/gold_marks_trades.pkl'); P = pd.read_pickle(f'{S}/feat/gold_proxies.pkl')
k = np.clip(P.index.searchsorted(X.t, 'right') - 1, 0, len(P) - 1)
ADOPT = ['S', 'Q', 'L2']
rows = []
for c in P.columns:
    v = P[c].to_numpy()[k]; keep = v != -X.side.to_numpy()        # drop only trades against the proxy
    for grp, msk in (('採用3本', X.ea.isin(ADOPT)), ('全8種', np.ones(len(X), bool))):
        for h in (1, 2):
            a = X[msk & (X.half == h)]; kk = keep[(msk & (X.half == h)).to_numpy()]
            rows.append(dict(判定=c, 対象=grp, half=h, 元R=a.R.sum(), 残R=a.R[kk].sum(), 外した回数=int((~kk).sum()), 外したR=a.R[~kk].sum(), 外した平均=a.R[~kk].mean()))
D = pd.DataFrame(rows)
for grp, g in D.groupby('対象'):
    t = g.pivot(index='判定', columns='half', values=['外した回数', '外したR', '外した平均']).round(2)
    t.columns = [f'{a}_{b}' for a, b in t.columns]
    print(f'\n### {grp}：判定と逆向きのトレードを外すと（外したトレードの合計Rがマイナスなら外して得）')
    print(t.sort_values('外したR_1').to_string())
for ea in ADOPT + ['C', 'J3', 'P', 'DIP', 'U']:
    a = X[X.ea == ea]; v = P['dow4P'].to_numpy()[k][(X.ea == ea).to_numpy()]; ag = v == -a.side.to_numpy()
    print(f'{ea:4s} 仮ダウと逆: 前半 {a[ag & (a.half == 1)].R.sum():+6.1f}R（{(ag & (a.half == 1)).sum()}回） 後半 {a[ag & (a.half == 2)].R.sum():+6.1f}R（{(ag & (a.half == 2)).sum()}回）')
