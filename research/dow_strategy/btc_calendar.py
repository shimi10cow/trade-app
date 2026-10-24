"""Bitcoin calendar / hours (2026-10-24): BTC trades every day, so the weekend is part of the week.
Halves 2017-21 / 2022-26. Daily returns in units of the previous 20-day ATR(D1) (broker days):
  1. day of the week (Mon..Sun), mean, t, share of up days; weekend vs weekdays range
  2. position in the month (last 2 days / first 4 / rest)
  3. JST hour: mean signed move of each hour in units of the median hourly range, and the hour's activity
Then the BTC EA trades (core EAs + S buys) by entry weekday and month start."""
import numpy as np, pandas as pd, glob, os
import new_summary as N
S = N.S
m = pd.read_csv(f'{S}/ws_BTCUSD/M15_broker.csv', parse_dates=['time']).set_index('time')     # log prices
D = pd.DataFrame(dict(c=m.close.resample('1D').last(), h=m.high.resample('1D').max(), l=m.low.resample('1D').min())).dropna()
D['ret'] = D.c.diff(); tr = np.maximum(D.h - D.l, np.maximum((D.h - D.c.shift()).abs(), (D.l - D.c.shift()).abs()))
D['atr'] = tr.rolling(20).mean().shift(); D['z'] = D.ret / D.atr; D['rng'] = tr / D.atr
D = D.dropna(); D['half'] = np.where(D.index.year <= 2021, 1, 2)
D['wd'] = D.index.dayofweek.map(dict(enumerate('月火水木金土日')))
ym = D.index.to_period('M'); D['pos'] = D.groupby(ym).cumcount() + 1; D['neg'] = D.groupby(ym).cumcount(ascending=False) + 1
D['mp'] = np.where(D.neg <= 2, '月末2日', np.where(D.pos <= 4, '月初4日', 'それ以外'))
t = lambda x: x.mean() / (x.std() / np.sqrt(len(x)))
pd.set_option('display.width', 220)
print('== 1. 曜日（日足の動き、ATR 単位）')
print(D.groupby(['wd', 'half']).agg(n=('z', 'size'), mean=('z', 'mean'), t=('z', t), up=('z', lambda x: (x > 0).mean()), 値幅=('rng', 'mean')).unstack('half').round(2).reindex(list('月火水木金土日')).to_string())
print('\n== 2. 月の中の位置'); print(D.groupby(['mp', 'half']).agg(n=('z', 'size'), mean=('z', 'mean'), t=('z', t)).unstack('half').round(2).to_string())
# 3. JST hours
tj = pd.DatetimeIndex(m.index).tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').tz_convert('Asia/Tokyo').tz_localize(None)
H = pd.DataFrame(dict(o=m.open.to_numpy(), c=m.close.to_numpy(), h=m.high.to_numpy(), l=m.low.to_numpy()), index=tj)
H = H[H.index.notna()]; H = H[~H.index.duplicated()]
h1 = H.resample('1h').agg(dict(o='first', c='last', h='max', l='min')).dropna()
h1['mv'] = h1.c - h1.o; h1['rg'] = h1.h - h1.l; med = h1.rg.rolling(24 * 20).median().shift()
h1['z'] = h1.mv / med; h1['act'] = h1.rg / med; h1 = h1.dropna(); h1['half'] = np.where(h1.index.year <= 2021, 1, 2)
g = h1.groupby([h1.index.hour, 'half']).agg(mean=('z', 'mean'), t=('z', t), act=('act', 'mean')).unstack('half').round(3)
print('\n== 3. 日本時間ごと（1 時間の動き、1 時間の値幅の中央＝1）'); print(g.to_string())
# 4. EA trades
rows = []
for ea, f in N.CORE:
    x = N.load('BTCUSD', f)
    if x is not None: rows.append(x.assign(key=ea))
for f in sorted(glob.glob(f'{S}/ws_BTCUSD/research/dow_strategy/results/st2/S_*buy*.csv'))[:1]:
    x = N.load('BTCUSD', 'st2/' + os.path.basename(f)); rows.append(x.assign(key='S買い'))
X = pd.concat(rows); X['wd'] = X.tt.dt.dayofweek.map(dict(enumerate('月火水木金土日')))
k = np.clip(D.index.searchsorted(X.tt.dt.normalize()), 0, len(D) - 1); X['ms'] = D.pos.to_numpy()[k] <= 3
print('\n== 4. BTC の EA のトレード：入った曜日（平均R、前半/後半）')
print(X.groupby(['wd', 'half']).R.agg(['size', 'mean']).unstack('half').round(2).reindex(list('月火水木金土日')).to_string())
print('\n   月初 3 日か'); print(X.groupby(['ms', 'half']).R.agg(['size', 'mean']).unstack('half').round(2).to_string())
