"""Does the NFP reaction go against the week's trend? (user, 2026-10-23) Gold / USDJPY / EURUSD, M15 broker data.
Week trend = move from the week's first bar (Sunday/Monday open) to the bar just before 08:30 NY Friday, in ATR(D1) units.
Reaction = move from that bar to +1h, +4h and the week's last bar (Friday close), signed against... reported as 'with the
week trend' (+) / 'against' (-). Compared with ordinary Fridays at the same clock time (placebo)."""
import numpy as np, pandas as pd, nfp_study as NS
S = NS.S
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv', 'USDJPY': f'{S}/ws_USDJPY/M15_broker.csv', 'XAUUSD': f'{S}/ws_XAUUSD/M15_broker.csv'}
fr = pd.date_range('2005-01-07', '2026-10-16', freq='W-FRI')
F = pd.DatetimeIndex([pd.Timestamp(d.year, d.month, d.day, 8, 30).tz_localize('America/New_York').tz_convert('Europe/Athens').tz_localize(None) for d in fr])
isn = np.isin(F.normalize(), NS.NFP.normalize())
rows = []
for pair, f in M15.items():
    m = pd.read_csv(f, parse_dates=['time']).set_index('time'); c = m.close
    if c.median() < 20 and pair == 'XAUUSD': c = np.exp(c)
    d1 = m.resample('1D').agg(dict(high='max', low='min', close='last')).dropna()
    if pair == 'XAUUSD': d1 = np.exp(d1)
    atr = (d1.high - d1.low).rolling(20).mean()
    T = c.index
    for t, nf in zip(F, isn):
        i = T.searchsorted(t) - 1                                    # last bar before the release
        if i < 100 or i + 20 >= len(T): continue
        wk0 = T.searchsorted(t.normalize() - pd.Timedelta(days=t.dayofweek))  # Monday 00:00 broker
        a = atr.iloc[max(0, atr.index.searchsorted(t.normalize()) - 1)]
        if not np.isfinite(a) or a <= 0 or wk0 >= i: continue
        wk = (c.iloc[i] - c.iloc[wk0]) / a; s = np.sign(wk)
        end = T.searchsorted(t.normalize() + pd.Timedelta('23h59min')) - 1
        r = {f'+{k}h': s * (c.iloc[min(i + 4 * k, len(T) - 1)] - c.iloc[i]) / a for k in (1, 4)}
        r['金曜終値まで'] = s * (c.iloc[end] - c.iloc[i]) / a
        rows.append(dict(pair=pair, t=t, nfp=nf, wk=wk, half=1 if t.year <= 2015 else 2, **r))
D = pd.DataFrame(rows)
D['週の強さ'] = pd.cut(D.wk.abs(), [0, 0.5, 1, 2, 99], labels=['小(<0.5ATR)', '中(0.5-1)', '大(1-2)', '特大(>2)'])
pd.set_option('display.width', 220)
for col in ('+1h', '+4h', '金曜終値まで'):
    print(f'\n### 発表から {col} の動き（週のトレンドと同じ向き=+、逆=-、ATR(D1)単位の平均）と「逆に動いた割合」')
    g = D.groupby(['pair', 'nfp', 'half'])[col].agg(['mean', lambda x: (x < 0).mean(), 'count']).round(3)
    g.columns = ['平均', '逆に動いた割合', '回数']; print(g.unstack('nfp').to_string())
print('\n### 週のトレンドの強さ別（NFP、金曜終値まで、平均・逆の割合）')
g = D[D.nfp].groupby(['pair', '週の強さ', 'half'], observed=True)['金曜終値まで'].agg(['mean', lambda x: (x < 0).mean(), 'count']).round(2)
g.columns = ['平均', '逆の割合', '回数']; print(g.to_string())
D.to_pickle(f'{S}/feat/nfp_week.pkl')
