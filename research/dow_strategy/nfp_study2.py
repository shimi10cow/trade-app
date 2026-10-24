"""NFP effect without the holding-time trap: classify trades only by ENTRY time relative to the nearest Friday 08:30 NY,
and compare NFP Fridays with the other Fridays (same clock time = placebo)."""
import numpy as np, pandas as pd, combo_stable as CS, nfp_study as NS
P = CS.POOL; P = P[P.pair.isin(['XAUUSD', 'USDJPY', 'EURUSD'])].copy(); P['tt'] = pd.to_datetime(P.tt)
P['half'] = np.where(P.tt.dt.year <= 2015, 1, 2)
fr = pd.date_range('2004-01-02', '2026-12-31', freq='W-FRI')
F = pd.DatetimeIndex([pd.Timestamp(d.year, d.month, d.day, 8, 30).tz_localize('America/New_York').tz_convert('Europe/Athens').tz_localize(None) for d in fr])
isnfp = np.isin(F.normalize(), NS.NFP.normalize())
d = (P.tt.to_numpy()[:, None] - F.to_numpy()[None, :]) / np.timedelta64(1, 'h')     # hours from each Friday 08:30
d = np.where(np.abs(d) <= 48, d, np.nan)
j = np.nanargmin(np.where(np.isnan(d), np.inf, np.abs(d)), axis=1); h = d[np.arange(len(P)), j]
P['h'] = h; P['nfp'] = np.where(np.isnan(h), 'その他', np.where(isnfp[j], 'NFP金曜', 'ふつうの金曜'))
P['win'] = pd.cut(P.h, [-48, -24, -4, 0, 4, 24, 48], labels=['前48-24h', '前24-4h', '前4h以内', '後4h以内', '後4-24h', '後24-48h'])
X = P[P.nfp != 'その他']
for pair, g in X.groupby('pair'):
    t = g.groupby(['win', 'nfp', 'half'], observed=True).R.mean().unstack(['nfp', 'half']).round(2)
    n = g.groupby(['win', 'nfp'], observed=True).size().unstack('nfp')
    print(f'\n== {pair}（平均R、NFP金曜 vs ふつうの金曜、前半/後半）'); print(pd.concat([t, n.add_prefix('回数_')], axis=1).to_string())
A = X[X.key.isin(CS.P['④ ③＋US30（T・Q）'])]
print('\n== 採用中の EA（3 銘柄）')
t = A.groupby(['win', 'nfp', 'half'], observed=True).R.agg(['mean', 'count']).unstack(['nfp', 'half']).round(2); print(t.to_string())
