"""Trading hours (2026-10-23). JST hours throughout.
(1) Market: mean signed return per JST hour (in units of the median hourly range) and the hour's activity, by half.
    'Consistent drift' = same sign in both halves and |mean| >= 0.05.
(2) EA trades (combo ④ + candidates): mean R by JST entry block (0-3, 3-6, ... 21-24) per EA and half.
(3) Rule check: per EA, drop the blocks whose first-half mean R < 0 (with >= 15 trades) -> second-half change."""
import numpy as np, pandas as pd, combo_stable as CS, new_summary as N
S = CS.S
SRC = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv', 'USDJPY': f'{S}/ws_USDJPY/M15_broker.csv', 'XAUUSD': f'{S}/ws_XAUUSD/M15_broker.csv',
       'XAGUSD': f'{S}/ws_XAGUSD/M15_broker.csv', 'US30': f'{S}/ws_US30/M15_broker.csv', 'JP225': f'{S}/ws_JP225/M15_broker.csv', 'US500': f'{S}/ws_US500/M15_broker.csv'}
SPLIT = {'US30': 2020, 'JP225': 2021, 'US500': 2021}
def jst(t): return pd.DatetimeIndex(t).tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').tz_convert('Asia/Tokyo')
print('### (1) 相場：日本時間ごとの平均の動き（1 時間の値幅の中央値を 1 とした単位、前半/後半）。前後半とも同じ向きで 0.05 以上を表示')
for sym, f in SRC.items():
    m = pd.read_csv(f, parse_dates=['time']).set_index('time'); c = m.close
    if c.median() > 20: c = np.log(c)
    h1 = c.resample('1h').last().dropna(); hi = m.high.resample('1h').max(); lo = m.low.resample('1h').min()
    if m.close.median() > 20: hi, lo = np.log(hi), np.log(lo)
    rng = (hi - lo).reindex(h1.index); r = h1.diff(); u = r / rng.median()
    j = jst(h1.index); ok = ~pd.isna(j)
    d = pd.DataFrame(dict(u=u.to_numpy()[ok], act=(rng / rng.median()).to_numpy()[ok], h=j[ok].hour, y=j[ok].year)).dropna()
    d['half'] = np.where(d.y <= SPLIT.get(sym, 2015), 1, 2)
    g = d.groupby(['h', 'half']).u.mean().unstack('half'); a = d.groupby('h').act.mean()
    cons = g[(np.sign(g[1]) == np.sign(g[2])) & (g.abs().min(axis=1) >= 0.05)]
    top = a.sort_values(ascending=False).index[:4].tolist()
    print(f'{sym}: 上がりやすい {[(h, round(v1, 2), round(v2, 2)) for h, (v1, v2) in cons[cons[1] > 0].iterrows()]} '
          f'下がりやすい {[(h, round(v1, 2), round(v2, 2)) for h, (v1, v2) in cons[cons[1] < 0].iterrows()]} | よく動く時間 {top}')
# (2)(3) EA trades
keys = CS.P['④ ③＋US30（T・Q）']; X = CS.mk(keys); X['tt'] = pd.to_datetime(X.tt)
extra = [N.load(s, 'rsi2/M_200_10_ma5_st.csv').assign(key=f'M@{s}', pair=s) for s in ('US30', 'US500')]
extra.append(N.load('JP225', 'tl_N2.csv').assign(key='L@JP225', pair='JP225'))
X = pd.concat([X[['R', 'tt', 'key', 'pair']]] + [e[['R', 'tt', 'key', 'pair']] for e in extra], ignore_index=True)
j = jst(X.tt); X['h'] = j.hour; X['blk'] = (X.h // 3) * 3
X['half'] = [1 if y <= SPLIT.get(p, 2015) else 2 for y, p in zip(X.tt.dt.year, X.pair)]
X = X.dropna(subset=['h'])
print('\n### (2) EA のトレード：入った時間帯（日本時間 3 時間ごと）の平均R 前半/後半（回数）')
t = X.groupby(['blk', 'half']).R.agg(['mean', 'count']).unstack('half').round(2); print(t.to_string())
print('\n### 銘柄ごと（平均R 前半/後半）')
for p, g in X.groupby('pair'):
    print(p, ' '.join(f"{int(b):02d}時:{v[1]:+.2f}/{v[2]:+.2f}" for b, v in g.groupby(['blk', 'half']).R.mean().unstack('half').iterrows()))
print('\n### (3) EA ごとに「前半で平均マイナスの時間帯（15 回以上）」を外すと')
tot1 = tot2 = 0; rows = []
for k, g in X.groupby('key'):
    a = g[g.half == 1]; st = a.groupby('blk').R.agg(['mean', 'count']); bad = st[(st['mean'] < 0) & (st['count'] >= 15)].index.tolist()
    b = g[g.half == 2]; d2 = -b[b.blk.isin(bad)].R.sum(); d1 = -a[a.blk.isin(bad)].R.sum()
    rows.append(dict(EA=k, 外す時間帯=','.join(f'{int(x):02d}' for x in bad), 前半の改善=round(d1, 1), 後半の改善=round(d2, 1), 後半で外れる回数=int(b.blk.isin(bad).sum())))
R = pd.DataFrame(rows); print(R.to_string(index=False)); print(f'後半の改善 合計 {R.後半の改善.sum():+.1f}R、良くなった EA {(R.後半の改善 > 0).sum()}・悪くなった {(R.後半の改善 < 0).sum()}')
X.to_pickle(f'{S}/feat/hour_trades.pkl')
