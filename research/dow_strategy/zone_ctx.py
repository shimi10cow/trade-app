"""Context for the zone counter-move trades: is the bounce better when the market is in a range (H4 range score at entry,
same recipe as range_check.py)? Pooled over all zone settings per instrument; halves."""
import numpy as np, pandas as pd, new_summary as N
S = N.S
A = pd.read_pickle(f'{S}/feat/zone_trades.pkl')
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'}
out = []
for sym, g in A.groupby('sym'):
    m = pd.read_csv(M15.get(sym, f'{S}/ws_{sym}/M15_broker.csv'), parse_dates=['time']).set_index('time')
    h = m.resample('4h').agg(dict(high='max', low='min', close='last')).dropna()
    pc = h.close.shift(); atr = np.maximum(h.high - h.low, np.maximum((h.high - pc).abs(), (h.low - pc).abs())).rolling(14).mean(); ma = h.close.rolling(75).mean()
    f = pd.DataFrame(dict(a=(h.close - ma).abs() / atr, b=(ma - ma.shift(10)).abs() / atr, c=(h.close - h.close.shift(50)).abs() / h.close.diff().abs().rolling(50).sum()))
    rs = pd.Series(np.nanmean(np.vstack([1 - f[k].rolling(3000, min_periods=1500).rank(pct=True) for k in f]), axis=0), index=h.index + pd.Timedelta('4h'))
    i = rs.index.searchsorted(g.tt.to_numpy(), 'right') - 1
    g = g.copy(); g['rs'] = np.where(i >= 0, rs.to_numpy()[np.maximum(i, 0)], np.nan); out.append(g)
A = pd.concat(out); A = A[A.rs.notna()]
A['場面'] = pd.cut(A.rs, [0, 0.4, 0.6, 0.7, 1], labels=['トレンド', '中間', 'ややレンジ', 'レンジ'])
print('### 全設定・全銘柄：場面ごとの平均R（前半／後半）'); print(A.groupby(['場面', 'half'], observed=True).R.agg(['count', 'mean']).unstack('half').round(3).to_string())
print('\n### 銘柄ごと：レンジ(>0.7) − それ以外 の平均R差（前半／後半）')
w = A.assign(r=A.rs > 0.7).groupby(['sym', 'half', 'r']).R.mean().unstack('r'); w = (w[True] - w[False]).unstack('half').round(3)
print(w.to_string()); print('前後半とも+ :', ((w[1] > 0) & (w[2] > 0)).sum(), ' 前後半とも- :', ((w[1] < 0) & (w[2] < 0)).sum(), '/', len(w))
A.to_pickle(f'{S}/feat/zone_trades_rs.pkl')
