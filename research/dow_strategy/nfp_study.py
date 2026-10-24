"""US employment report (NFP) and the EA trades (2026-10-23). Release = 08:30 New York on the Friday three weeks after the
week (Sun-Sat) that contains the 12th (BLS rule; a few government-shutdown delays are not modelled). Times converted to
broker time (Europe/Athens) like the trade files.
Each trade of gold / USDJPY / EURUSD: 'pre' = entered within 24h before a release, 'across' = open at a release, 'none'."""
import numpy as np, pandas as pd, combo_stable as CS
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
def nfp_dates(y0=2004, y1=2026):
    out = []
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            d12 = pd.Timestamp(y, m, 12); sat = d12 + pd.Timedelta(days=(5 - d12.dayofweek) % 7)
            rel = sat + pd.Timedelta(days=20)
            if rel.dayofweek != 4: rel = rel + pd.Timedelta(days=(4 - rel.dayofweek) % 7)
            t = pd.Timestamp(rel.year, rel.month, rel.day, 8, 30).tz_localize('America/New_York').tz_convert('Europe/Athens').tz_localize(None)
            out.append(t)
    return pd.DatetimeIndex(sorted(out))
NFP = nfp_dates()
pd.Series(NFP).to_csv(f'{S}/feat/nfp_dates.csv', index=False)
if __name__ == '__main__':
    P = CS.POOL; P = P[P.pair.isin(['XAUUSD', 'USDJPY', 'EURUSD'])].copy(); P['tt'] = pd.to_datetime(P.tt); P['et'] = pd.to_datetime(P.et)
    P['half'] = np.where(P.tt.dt.year <= 2015, 1, 2)
    i = NFP.searchsorted(P.tt); nxt = NFP[np.minimum(i, len(NFP) - 1)]
    pre = (nxt - P.tt <= pd.Timedelta('24h')) & (nxt > P.tt)
    across = (nxt > P.tt) & (nxt < P.et)
    P['nfp'] = np.where(pre & across, '前24h入り・またぐ', np.where(across, 'またぐ', np.where(pre, '前24h入り・前に決済', 'なし')))
    print('NFP 回数', len(NFP), NFP[-3:].tolist())
    g = P.groupby(['pair', 'nfp', 'half']).R.agg(['count', 'mean']).unstack('half').round(3); print(g.to_string())
    print('\n採用中の EA だけ（④）:')
    A = P[P.key.isin(CS.P['④ ③＋US30（T・Q）'])]
    print(A.groupby(['nfp', 'half']).R.agg(['count', 'mean', 'sum']).unstack('half').round(2).to_string())
    w = A.groupby(['key', 'nfp', 'half']).R.mean().unstack('half').round(2); print(w.to_string())
