"""Would 'skip entries while the market is in a range' have helped? (user's discretionary rule, 2026-10-23)
Range score per H4 bar (same recipe as range_detect.range_score: past-only percentile of |dev from SMA75|, SMA75 slope,
efficiency ratio 50, high = range-like), looked up at each entry (last closed H4 bar). Trades from feat/tp_eval.pkl."""
import numpy as np, pandas as pd, new_summary as N
S = N.S
D = pd.read_pickle(f'{S}/feat/tp_eval.pkl')
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'}
out = []
for pair, g in D.groupby('pair'):
    m = pd.read_csv(M15.get(pair, f'{S}/ws_{pair}/M15_broker.csv'), parse_dates=['time']).set_index('time')
    h = m.resample('4h').agg(dict(high='max', low='min', close='last')).dropna()
    pc = h.close.shift(); atr = np.maximum(h.high - h.low, np.maximum((h.high - pc).abs(), (h.low - pc).abs())).rolling(14).mean()
    ma = h.close.rolling(75).mean()
    f = pd.DataFrame(dict(absdev=(h.close - ma).abs() / atr, slope=(ma - ma.shift(10)).abs() / atr,
                          er=(h.close - h.close.shift(50)).abs() / h.close.diff().abs().rolling(50).sum()))
    rs = np.nanmean(np.vstack([1 - f[k].rolling(3000, min_periods=1500).rank(pct=True) for k in f]), axis=0)
    s = pd.Series(rs, index=h.index + pd.Timedelta('4h'))          # known when the bar has closed
    i = s.index.searchsorted(g.tt.to_numpy(), 'right') - 1
    g = g.copy(); g['rs'] = np.where(i >= 0, s.to_numpy()[np.maximum(i, 0)], np.nan); out.append(g)
D = pd.concat(out); D = D[D.rs.notna()]
D['場面'] = pd.cut(D.rs, [0, 0.4, 0.6, 0.7, 1], labels=['トレンド(<0.4)', '中間(0.4-0.6)', 'ややレンジ(0.6-0.7)', 'レンジ(>0.7)'])
KEEP = ['R@EURUSD', 'T2@EURUSD', 'L@EURUSD', 'A@EURUSD', 'C@EURUSD', 'C@USDJPY', 'J2@USDJPY', 'L2@XAUUSD', 'S@XAUUSD', 'Q@XAUUSD', 'Q@XAGUSD', 'T@US30', 'Q@US30']
X = D[D.key.isin(KEEP)]
pd.set_option('display.width', 220)
print('### 採用候補 13 本：場面ごと（回数・平均R・合計R、前半／後半）')
g = X.groupby(['場面', 'half'], observed=True).R.agg(['count', 'mean', 'sum']).round(2).unstack('half'); print(g.to_string())
print('\n### EA ごと：レンジ(>0.7)での合計R 前半／後半（レンジ以外の平均R と比べて）')
for k, h in X.groupby('key'):
    r = h[h.rs > 0.7]; o = h[h.rs <= 0.7]
    print(f'{k:11s} レンジ {len(r[r.half==1]):3d}回 {r[r.half==1].R.sum():+6.1f}R / {len(r[r.half==2]):3d}回 {r[r.half==2].R.sum():+6.1f}R | 平均 レンジ {r.R.mean():+.2f} vs それ以外 {o.R.mean():+.2f}')
print('\n### 全 EA・全銘柄（参考）：場面ごとの平均R 前半／後半')
print(D.groupby(['場面', 'half'], observed=True).R.mean().unstack('half').round(3).to_string())
D[['key', 'tt', 'R', 'half', 'rs']].to_pickle(f'{S}/feat/range_check.pkl')
