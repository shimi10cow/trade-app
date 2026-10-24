"""Calendar effects (user, 2026-10-23): turn of the month and day of the week.
Daily bars from the broker M15 data (broker day). For every instrument, by half:
  1. day of the week: mean daily return in units of ATR(D1, 20) of the day before, share of up days, t value
  2. turn of the month: day position in the month (last 2 trading days = -2/-1, first 4 = 1..4, rest = mid)
  3. simple TOM trade: buy at the close 2 trading days before the month end, sell at the close of the 3rd trading day,
     cost = the instrument's round-trip cost; result in % and in R (stop distance 2 x ATR(D1) for comparison)
  4. adopted EA trades (trade_pool) by entry weekday and month position
Writes nothing but the printout; feat/cal_daily.pkl keeps the daily table."""
import numpy as np, pandas as pd
import trade_pool as TP
S = TP.S
SRC = {'EURUSD': (f'{S}/EURUSD_M15_long_broker.csv', False), 'USDJPY': (f'{S}/ws_USDJPY/M15_broker.csv', False)}
SYMS = ['EURUSD', 'USDJPY', 'XAUUSD', 'XAGUSD', 'US30', 'US500', 'JP225', 'OIL']
SPLIT = {'US30': 2020, 'US500': 2021, 'JP225': 2021, 'OIL': 2021}
COST = {'EURUSD': 1.2e-4 / 1.2, 'USDJPY': 1.2e-4 / 110 * 100 / 100, 'XAUUSD': 6e-5, 'XAGUSD': 8e-4, 'US30': 1.5e-4, 'US500': 1.5e-4, 'JP225': 3e-4, 'OIL': 6e-4}
rows = []
for sym in SYMS:
    f, lg = SRC.get(sym, (f'{S}/ws_{sym}/M15_broker.csv', True))
    m = pd.read_csv(f, parse_dates=['time']).set_index('time')
    c = m.close if lg else np.log(m.close)
    h = m.high if lg else np.log(m.high); l = m.low if lg else np.log(m.low)
    D = pd.DataFrame(dict(c=c.resample('1D').last(), h=h.resample('1D').max(), l=l.resample('1D').min())).dropna()
    D = D[D.index.dayofweek < 5]
    D['ret'] = D.c.diff(); tr = np.maximum(D.h - D.l, np.maximum((D.h - D.c.shift()).abs(), (D.l - D.c.shift()).abs()))
    D['atr'] = tr.rolling(20).mean().shift(); D['z'] = D.ret / D.atr
    ym = D.index.to_period('M'); D['pos'] = D.groupby(ym).cumcount() + 1; D['neg'] = D.groupby(ym).cumcount(ascending=False) + 1
    D['mpos'] = np.where(D.neg <= 2, 'end' + (-D.neg).astype(str), np.where(D.pos <= 4, 'start' + D.pos.astype(str), 'mid'))
    D['half'] = np.where(D.index.year <= SPLIT.get(sym, 2015), 1, 2); D['sym'] = sym
    rows.append(D.dropna(subset=['z']))
A = pd.concat(rows); A.to_pickle(f'{S}/feat/cal_daily.pkl')
pd.set_option('display.width', 230)
A['wd'] = A.index.dayofweek.map(dict(enumerate(['月', '火', '水', '木', '金'])))


def tab(col, order):
    g = A.groupby(['sym', col, 'half']).z.agg(['mean', 'count', 'std']).reset_index()
    g['t'] = g['mean'] / (g['std'] / np.sqrt(g['count']))
    p = g.pivot_table(index=['sym', col], columns='half', values=['mean', 't']).round(2)
    return p.reindex(order, level=1)


print('== 1. 曜日ごとの平均（ATR 単位、t=|2| 以上が目安）'); print(tab('wd', ['月', '火', '水', '木', '金']).to_string())
print('\n== 2. 月の中の位置（end-2/-1 = 月末 2 日、start1-4 = 月初 4 日）')
print(tab('mpos', ['end-2', 'end-1', 'start1', 'start2', 'start3', 'start4', 'mid']).to_string())
# 3. simple TOM trade: hold from close of end-3 (3rd last day) to close of start3  => days end-2, end-1, start1..3
out = []
for sym, D in A.groupby('sym'):
    D = D.copy(); ym = D.index.to_period('M')
    for p, g in D.groupby(ym):
        nx = D[ym == p + 1]
        e3 = g[g.neg == 3]
        if not len(e3) or len(nx) < 3: continue
        en = e3.c.iloc[0]; ex = nx.c.iloc[2]; a = e3.atr.iloc[0]
        r = ex - en - COST[sym]
        out.append(dict(sym=sym, t=e3.index[0], ret=r, R=r / (2 * a), half=e3.half.iloc[0]))
T = pd.DataFrame(out)
print('\n== 3. 月末月初に買って持つだけ（月末 3 日前の終値 → 翌月 3 日目の終値、コスト込み）')
print(T.groupby(['sym', 'half']).agg(n=('R', 'size'), 平均R=('R', 'mean'), 勝率=('R', lambda x: (x > 0).mean()), 合計R=('R', 'sum'), 平均pct=('ret', lambda x: x.mean() * 100)).round(3).unstack('half').to_string())
# 4. EA trades
X = TP.load_all(); X = X[X.adopt].copy(); X['wd'] = X.tt.dt.dayofweek.map(dict(enumerate(['月', '火', '水', '木', '金', '土', '日'])))
dd = X.tt.dt.normalize(); ym = X.tt.dt.to_period('M')
pos = []
for sym, g in X.groupby('pair'):
    days = A[A.sym == sym][['pos', 'neg']]
    k = days.index.searchsorted(g.tt.dt.normalize())
    k = np.clip(k, 0, len(days) - 1); p = days.pos.to_numpy()[k]; n = days.neg.to_numpy()[k]
    pos.append(pd.Series(np.where(n <= 2, '月末2日', np.where(p <= 3, '月初3日', 'それ以外')), index=g.index))
X['mp'] = pd.concat(pos)
print('\n== 4. 採用 EA のトレード：入った曜日（平均R・回数）')
print(X.groupby(['wd', 'half']).R.agg(['size', 'mean']).unstack('half').round(3).reindex(['月', '火', '水', '木', '金', '日']).to_string())
print('\n   入った日が月末月初か'); print(X.groupby(['mp', 'half']).R.agg(['size', 'mean']).unstack('half').round(3).to_string())
print('\n   銘柄 × 曜日（平均R 前半/後半）'); print(X.groupby(['pair', 'wd', 'half']).R.mean().unstack('half').round(2).unstack('wd').to_string())
