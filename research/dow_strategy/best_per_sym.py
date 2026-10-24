"""Best EA per instrument with details (XM costs). 'Best' = both halves positive, highest min(PF1, PF2)."""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl'); A = pd.read_pickle(f'{S}/feat/all_trades_new.pkl')
Q = pd.read_pickle(f'{S}/feat/q_best.pkl'); Q = Q.copy(); Q['key'] = 'Q@' + Q.pair; Q['ea'] = 'Q'
if 'half' not in Q: Q['half'] = np.where(Q.tt.dt.year <= (2021 if False else 2015), 1, 2)
Q.loc[Q.pair == 'BTCUSD', 'half'] = np.where(Q[Q.pair == 'BTCUSD'].tt.dt.year <= 2021, 1, 2)
X = pd.concat([T, A[~A.pair.isin(T.pair.unique())], Q[~Q.key.isin(T.key)]], ignore_index=True)
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
def det(g):
    g = g.sort_values('et'); r = g.R.to_numpy(); eq = np.cumsum(r); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    ls = mx = 0
    for v in r: ls = ls + 1 if v <= 0 else 0; mx = max(mx, ls)
    y = g.groupby(g.et.dt.year).R.sum(); yrs = g.tt.dt.year.max() - g.tt.dt.year.min() + 1
    a = g[g.half == 1].R; b = g[g.half == 2].R
    return dict(n=len(r), 年回数=len(r) / yrs, 勝率=(r > 0).mean(), 平均R=r.mean(), 合計R=r.sum(), PF=pf(g.R), 前半R=a.sum(), 前半PF=pf(a), 後半R=b.sum(), 後半PF=pf(b),
                最大DD_R=dd, 最大連敗=mx, 買いR=g[g.side == 1].R.sum() if 'side' in g and g.side.notna().any() else np.nan, 売りR=g[g.side == -1].R.sum() if 'side' in g and g.side.notna().any() else np.nan,
                黒字年=f'{(y > 0).sum()}/{len(y)}', 最良年=f'{y.idxmax()} {y.max():+.0f}', 最悪年=f'{y.idxmin()} {y.min():+.0f}', 上位5回の割合=pd.Series(r).nlargest(5).sum() / r.sum() if r.sum() > 0 else np.nan)
rows = []
for sym, h in X.groupby('pair'):
    c = []
    for k, g in h.groupby('key'):
        a = g[g.half == 1].R; b = g[g.half == 2].R
        if len(a) >= 20 and len(b) >= 20: c.append((min(pf(a), pf(b)), a.sum() > 0 and b.sum() > 0, k))
    c.sort(key=lambda z: (z[1], z[0]), reverse=True)
    for sc, ok, k in c[:2]: rows.append(dict(銘柄=sym, EA=k.split('@')[0], 両方黒字=ok, **det(h[h.key == k])))
D = pd.DataFrame(rows); D.to_csv(f'{S}/best_per_sym.csv', index=False)
pd.set_option('display.width', 300); print(D.round(2).to_string(index=False))
