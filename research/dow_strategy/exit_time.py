"""Time stops and partial profit (2026-10-22), on the actual M15 paths of every trade in the master table.
Rules act only if they trigger before the original exit; otherwise the original R stays.
 ts{N}_{X}: after N hours, if the best gain so far is below X R, exit at that bar's close
 tl{N}:     after N hours, if the trade is losing at that bar's close, exit there
 pp{X}:     close half at +X R (the rest runs as before)
 cap{N}:    exit at the close N hours after entry, whatever happens"""
import sys
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'} | {p: f'{S}/ws_{p}/M15_broker.csv' for p in ('USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD')}
COST = {'XAUUSD': 2.5e-4, 'BTCUSD': 8e-4}
pair = sys.argv[1]
T = pd.read_pickle(f'{S}/feat/all_trades_hold.pkl'); T = T[T.pair == pair]
m = pd.read_csv(M15[pair], parse_dates=['time'])
t15 = m.time.to_numpy(); h = m.high.to_numpy(); l = m.low.to_numpy(); c = m.close.to_numpy()
k0 = np.searchsorted(t15, T.tt.to_numpy()[:50]); sc = np.median(T.entry.to_numpy()[:50] / c[np.minimum(k0, len(c) - 1)]); sc = 100.0 if sc < 0.05 else 1.0
h, l, c = h / sc, l / sc, c / sc
cost = COST.get(pair, 1.2e-4)
NS = (12, 24, 48, 96); XS = (0.5, 1.0)
rows = []
for x in T.itertuples():
    i0 = np.searchsorted(t15, np.datetime64(x.tt)); i1 = np.searchsorted(t15, np.datetime64(x.et))
    s, e, rk, R = x.side, x.entry, x.risk, x.R
    res = {'idx': x.Index}
    fav = ((h[i0:i1] - e) if s == 1 else (e - l[i0:i1])) / rk; best = np.maximum.accumulate(fav) if len(fav) else fav
    cl = (c[i0:i1] - e) * s / rk - cost / rk
    for N in NS:
        j = N * 4 - 1   # bar index N hours after entry
        for X in XS:
            res[f'ts{N}_{X}'] = cl[j] if j < len(cl) and best[j] < X else R
        res[f'tl{N}'] = cl[j] if j < len(cl) and cl[j] < 0 else R
        res[f'cap{N}'] = cl[j] if j < len(cl) else R
    for X in (1.0, 1.5, 2.0, 3.0):
        res[f'pp{X}'] = 0.5 * X + 0.5 * R if len(best) and best[-1] >= X else R
    rows.append(res)
D = pd.DataFrame(rows).set_index('idx'); D.to_pickle(f'{S}/feat/exit_time_{pair}.pkl'); print(pair, len(D), 'scale', sc)
