"""Where does the current portfolio earn? Regime of every trade at entry and of every trading day (2026-11).
Regimes per symbol from the research M15 caches (no look-ahead: values of the last closed D1 / W1 / H4 bar).
  wk  : weekly trend  +1 / -1 / 0  = close vs SMA13(W1) and SMA13 4-week slope agree
  dy  : daily trend   +1 / -1 / 0  = close vs SMA20(D1) and SMA20 5-day slope agree
  wd  : 'same' (wk = dy != 0), 'opp' (weekly correction: dy = -wk != 0), 'flat' (one of them 0)
  rng : daily range   = efficiency ratio of the last 20 D1 closes < 0.2
  big : after a big daily move = |60-day move| > 6 x ATR20(D1)
  conv: H4 MA convergence = |SMA20 - SMA75| / ATR14(H4) < 0.5 and smaller than 10 bars earlier
"""
import numpy as np, pandas as pd
X = pd.read_pickle('full/current.pkl')
SYMS = sorted(X.sym.unique()); DAY = {}
for s in SYMS:
    m = pd.read_pickle(f'stoch/m15_{s}.pkl').set_index('time')
    D = m.resample('1D').agg(dict(high='max', low='min', close='last')).dropna(); D = D[D.index.dayofweek < 5]
    W = m.resample('W-FRI').agg(dict(close='last')).dropna()
    H4 = m.resample('4h').agg(dict(high='max', low='min', close='last')).dropna()
    def atr(b, n):
        pc = b.close.shift(); return np.maximum(b.high - b.low, np.maximum((b.high - pc).abs(), (b.low - pc).abs())).rolling(n).mean()
    w13 = W.close.rolling(13).mean(); wk = np.where((W.close > w13) & (w13 > w13.shift(4)), 1, np.where((W.close < w13) & (w13 < w13.shift(4)), -1, 0))
    d20 = D.close.rolling(20).mean(); dy = np.where((D.close > d20) & (d20 > d20.shift(5)), 1, np.where((D.close < d20) & (d20 < d20.shift(5)), -1, 0))
    er = (D.close.diff(20).abs() / D.close.diff().abs().rolling(20).sum()).to_numpy()
    big = (D.close.diff(60).abs() / atr(D, 20)).to_numpy() > 6
    s20, s75 = H4.close.rolling(20).mean(), H4.close.rolling(75).mean(); gap = ((s20 - s75).abs() / atr(H4, 14))
    conv = ((gap < 0.5) & (gap < gap.shift(10))).to_numpy()
    # values known at the start of each trading day (previous closed bars)
    day = pd.DataFrame(index=D.index)
    day['wk'] = pd.Series(wk, index=W.index).reindex(D.index, method='ffill').shift(1)
    day['dy'] = pd.Series(dy, index=D.index).shift(1); day['er'] = pd.Series(er, index=D.index).shift(1)
    day['big'] = pd.Series(big, index=D.index).shift(1); day['conv'] = pd.Series(conv, index=H4.index).resample('1D').last().reindex(D.index).shift(1)
    day = day.dropna(); day['rng'] = day.er < 0.2
    day['wd'] = np.where((day.wk != 0) & (day.dy == day.wk), 'same', np.where((day.wk != 0) & (day.dy == -day.wk), 'opp', 'flat'))
    DAY[s] = day
# tag trades by entry day, P&L by exit day
rows = []
for s, g in X.groupby('sym'):
    d = DAY[s]; k = d.index.searchsorted(g.t.dt.normalize(), side='right') - 1; ok = k >= 0
    g = g[ok].copy(); r = d.iloc[k[ok]]
    for c in ('wk', 'dy', 'wd', 'rng', 'big', 'conv'): g[c] = r[c].to_numpy()
    g['with_wk'] = np.where(g.wk == 0, 'W横ばい', np.where(g.wk * g.side > 0, 'W順', 'W逆')); rows.append(g)
T = pd.concat(rows, ignore_index=True); T['Rw'] = T.R * T.w; T.to_pickle('regime/trades.pkl')
pd.to_pickle(DAY, 'regime/days.pkl')
def tab(col, lab):
    # days in each state (all symbols that the portfolio trades, weighted equally) and R per 100 symbol-days
    dd = pd.concat([DAY[s][col].astype(str).value_counts() for s in SYMS], axis=1).sum(axis=1)
    g = T.groupby(T[col].astype(str)).agg(回数=('R', 'size'), 平均R=('R', 'mean'), 合計R=('Rw', 'sum'), 勝率=('R', lambda r: (r > 0).mean()))
    g['期間の割合'] = dd / dd.sum(); g['100日あたりR'] = g.合計R / dd * 100; g['前半'] = T[T.t < '2016'].groupby(T[col].astype(str)).R.mean(); g['後半'] = T[T.t >= '2016'].groupby(T[col].astype(str)).R.mean()
    print(f'\n== {lab}'); print(g.round(3).to_string())
tab('wd', '週足と日足（same=同じ向き / opp=週足の調整中 / flat=どちらか横ばい）')
tab('rng', '日足レンジ（効率<0.2）')
tab('big', '直近60日で大きく動いた後')
tab('conv', 'H4 MA20/75 収束中')
g = T.groupby('with_wk').agg(回数=('R', 'size'), 平均R=('R', 'mean'), 合計R=('Rw', 'sum'), 勝率=('R', lambda r: (r > 0).mean()))
g['前半'] = T[T.t < '2016'].groupby('with_wk').R.mean(); g['後半'] = T[T.t >= '2016'].groupby('with_wk').R.mean()
print('\n== トレードの向き × 週足の向き'); print(g.round(3).to_string())
