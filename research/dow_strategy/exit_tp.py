"""Fixed take-profit on top of each EA's own exit (2026-10-23). Untested so far: earlier exit work only swapped trails.
For every trade, the best price reached (M15 high/low) between entry and the actual exit, in R. With a target of k R:
if it was reached -> R = k - cost, otherwise the original result stays. Writes feat/tp_mfe.pkl (trade table + mfe)."""
import numpy as np, pandas as pd, new_summary as N
S = N.S
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl')
A = pd.read_pickle(f'{S}/feat/all_trades_new.pkl')
Q = pd.read_pickle(f'{S}/feat/q_best.pkl').copy(); Q['key'] = 'Q@' + Q.pair; Q['ea'] = 'Q'
# new instruments: entry price needed -> reload with entry
rows = []
for k in A[A.pair.isin(N.COST)].key.unique():
    ea, sym = k.split('@')
    f = dict(N.CORE).get(ea)
    if f is None: continue
    d = pd.read_csv(f'{S}/ws_{sym}/research/dow_strategy/results/{f}'); x = N.load(sym, f)
    d = d.iloc[-len(x):] if len(d) >= len(x) else d
    x = x.copy(); x['entry'] = (d.entry.to_numpy())[-len(x):] if len(d) else np.nan; x['key'] = k; x['pair'] = sym; x['ea'] = ea; rows.append(x)
cols = ['R', 'tt', 'et', 'side', 'risk', 'entry', 'key', 'pair', 'half']
Q['half'] = np.where(Q.tt.dt.year <= 2015, 1, 2)
P = pd.concat([T[cols], Q[~Q.key.isin(T.key)][cols]] + [r[cols] for r in rows], ignore_index=True)
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'}
out = []
for pair, g in P.groupby('pair'):
    m = pd.read_csv(M15.get(pair, f'{S}/ws_{pair}/M15_broker.csv'), parse_dates=['time'])
    t = m.time.to_numpy(); hi = m.high.to_numpy(float); lo = m.low.to_numpy(float); cl = m.close.to_numpy(float)
    fns = (('raw', lambda v: v), ('/100', lambda v: v / 100), ('log', lambda v: np.log(np.maximum(v, 1e-12))))
    mfe = np.full(len(g), np.nan); units = []
    for key, h in g.groupby('key'):   # units can differ by source table, so detect per EA
        i0 = np.clip(np.searchsorted(t, h.tt.to_numpy()[:200]), 0, len(t) - 1); e = h.entry.to_numpy()[:200]
        best = min((np.nanmedian(np.abs(fn(cl[i0]) / e - 1)), nm, fn) for nm, fn in fns); fn = best[2]; units.append(f'{key}:{best[1]}')
        Hh = fn(hi); Ll = fn(lo)
        a = np.searchsorted(t, h.tt.to_numpy()); b = np.searchsorted(t, h.et.to_numpy()); pos = g.index.get_indexer(h.index)
        for j, s_, z, en, sd, rk in zip(pos, a, b, h.entry.to_numpy(), h.side.to_numpy(), h.risk.to_numpy()):
            if z <= s_ or not rk > 0: continue
            mfe[j] = ((Hh[s_:z].max() - en) if sd == 1 else (en - Ll[s_:z].min())) / rk
    best = (0, ' '.join(u for u in units if not u.endswith('raw')) or 'raw')
    g = g.copy(); g['mfe'] = mfe; out.append(g)
    print(f'{pair}: 単位 {best[1]}（ずれ中央 {best[0]:.4f}）, {len(g)} 回, mfe 欠け {np.isnan(mfe).sum()}', flush=True)
D = pd.concat(out, ignore_index=True)
# check: winners' mfe should be >= their R (sanity)
w = D[(D.R > 0.5) & D.mfe.notna()]; print('確認: 勝ちトレードで mfe >= R-0.3 の割合', round(((w.mfe >= w.R - 0.3)).mean(), 3))
D.to_pickle(f'{S}/feat/tp_mfe.pkl')
