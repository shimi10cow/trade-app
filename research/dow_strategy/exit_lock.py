"""Profit lock after a big run (untested so far; breakeven at +1R was bad): once the best price reaches a R,
the stop is raised to b R (never lowered). If price then comes back to b before the EA's own exit -> R = b - cost.
Path checked on M15 in time order. Choice on the first half only."""
import numpy as np, pandas as pd, new_summary as N
S = N.S
D = pd.read_pickle(f'{S}/feat/tp_eval.pkl')
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'}
LOCKS = [(3, 1.5), (4, 2), (4, 2.5), (5, 3), (6, 4), (8, 5)]
fns = (('raw', lambda v: v), ('/100', lambda v: v / 100), ('log', lambda v: np.log(np.maximum(v, 1e-12))))
for a, b in LOCKS: D[f'L{a}_{b}'] = D.R
for pair, g in D.groupby('pair'):
    m = pd.read_csv(M15.get(pair, f'{S}/ws_{pair}/M15_broker.csv'), parse_dates=['time'])
    t = m.time.to_numpy(); hi = m.high.to_numpy(float); lo = m.low.to_numpy(float); cl = m.close.to_numpy(float)
    for key, h in g.groupby('key'):
        h = h[h.mfe >= 3]
        if not len(h): continue
        i0 = np.clip(np.searchsorted(t, h.tt.to_numpy()[:200]), 0, len(t) - 1); e = h.entry.to_numpy()[:200]
        fn = min((np.nanmedian(np.abs(f(cl[i0]) / e - 1)), i, f) for i, (nm, f) in enumerate(fns))[2]
        for idx, x in h.iterrows():
            s_, z = np.searchsorted(t, x.tt), np.searchsorted(t, x.et)
            if x.side == 1: fav = (fn(hi[s_:z]) - x.entry) / x.risk; adv = (fn(lo[s_:z]) - x.entry) / x.risk
            else: fav = (x.entry - fn(lo[s_:z])) / x.risk; adv = (x.entry - fn(hi[s_:z])) / x.risk
            run = np.maximum.accumulate(fav)
            for a, b in LOCKS:
                k = np.argmax(run >= a) if (run >= a).any() else -1
                if k < 0: continue
                after = adv[k + 1:]          # bars after the one that reached a (same-bar order unknown -> skip it)
                if (after <= b).any(): D.at[idx, f'L{a}_{b}'] = b - x.cR   # exits at b, even if the trade later ran further
D['type'] = np.where(D.pair.isin({'USDJPY', 'XAUUSD', 'BTCUSD', 'XAGUSD'}), 'トレンド型', '戻り型')
c = ['R'] + [f'L{a}_{b}' for a, b in LOCKS]
print('### 型ごと 合計R（前半／後半）'); print(D.groupby(['type', 'half'])[c].sum().round(0).to_string())
print('\n### 銘柄ごと 後半−元（前半で効いた設定を見るため前半も）')
G = D.groupby(['pair', 'half'])[c].sum(); print((G[c[1:]].sub(G.R, axis=0)).round(0).unstack('half').to_string())
rows = []
for k, g in D.groupby('key'):
    a = g[g.half == 1]; b = g[g.half == 2]
    if len(a) < 30 or len(b) < 30: continue
    best = max(c, key=lambda z: a[z].sum()); rows.append(dict(key=k, sel=best, d1=a[best].sum() - a.R.sum(), d2=b[best].sum() - b.R.sum()))
R = pd.DataFrame(rows); ch = R[R.sel != 'R']
print(f'\nEA×銘柄で前半に選ぶ：{len(R)} 件中 {len(ch)} 件が利益ロックを選択 → 後半 良くなった {(ch.d2 > 0).sum()}・悪くなった {(ch.d2 < 0).sum()}・同じ {(ch.d2 == 0).sum()}、後半合計 {ch.d2.sum():+.1f}R')
D.to_pickle(f'{S}/feat/lock_eval.pkl')
