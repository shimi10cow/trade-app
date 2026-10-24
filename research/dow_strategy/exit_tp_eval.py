"""Evaluate fixed targets (feat/tp_mfe.pkl). k in 1..6R. Per EA x instrument and per instrument character.
Choice on the first half only."""
import numpy as np, pandas as pd, new_summary as N
S = N.S
D = pd.read_pickle(f'{S}/feat/tp_mfe.pkl')
CP = {'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'EURJPY': 2.0e-4, 'GBPUSD': 1.6e-4, 'XAUUSD': 2.5e-4, 'BTCUSD': 8e-4}
def cprice(p, e):
    if p in CP: return CP[p]
    c = N.COST[p]; return c[1] / 100 if c[0] == 'pct' else c[1] * c[2] / np.exp(e)   # new workspaces use log prices
D['cR'] = [cprice(p, e) / r for p, e, r in zip(D.pair, D.entry, D.risk)]
KS = [1, 1.5, 2, 3, 4, 6]
for k in KS: D[f'tp{k}'] = np.where(D.mfe >= k, k - D.cR, D.R)
TREND = {'USDJPY', 'XAUUSD', 'BTCUSD', 'XAGUSD'}
D['type'] = np.where(D.pair.isin(TREND), 'トレンド型', '戻り型')
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
c = ['R'] + [f'tp{k}' for k in KS]
print('### 銘柄の型ごと 合計R（前半／後半）')
g = D.groupby(['type', 'half'])[c].sum().round(0); print(g.to_string())
print('\n### 銘柄ごと 合計R（前半／後半）')
print(D.groupby(['pair', 'half'])[c].sum().round(0).unstack('half').to_string())
# per key: choose on first half (incl. 'none'), check second half
rows = []
for k, g in D.groupby('key'):
    a = g[g.half == 1]; b = g[g.half == 2]
    if len(a) < 30 or len(b) < 30: continue
    best = max(c, key=lambda z: a[z].sum())
    rows.append(dict(key=k, 選択=best, 前半差=a[best].sum() - a.R.sum(), 後半差=b[best].sum() - b.R.sum()))
R = pd.DataFrame(rows); ch = R[R.選択 != 'R']
print(f'\n### EA×銘柄ごとに前半で選ぶ：{len(R)} 件中 利確を選んだ {len(ch)} 件 → 後半で良くなった {(ch.後半差 > 0).sum()}・悪くなった {(ch.後半差 < 0).sum()}、後半の合計の変化 {ch.後半差.sum():+.1f}R')
D.to_pickle(f'{S}/feat/tp_eval.pkl')
