"""Cross-market agreement on the new instruments: does the related market point the same way when the trade opens?
 silver <- gold, JPY crosses <- USDJPY (yen side), USDCHF <- EURUSD (inverse), AUDUSD <- AUDJPY.
 agree_ma : related market's H4 close above/below its H4 SMA75 in the trade direction; agree_mv : its 24h move (ATR(H1)) same sign."""
import numpy as np, pandas as pd, new_summary as N
S = N.S
REL = {'XAGUSD': ('XAUUSD', 1), 'GBPJPY': ('USDJPY', 1), 'AUDJPY': ('USDJPY', 1), 'CADJPY': ('USDJPY', 1), 'CHFJPY': ('USDJPY', 1),
       'USDCHF': ('EURUSD', -1), 'AUDUSD': ('AUDJPY', 1), 'US30': ('USDJPY', 1)}
SRC = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'}
def m15(p): return SRC.get(p, f'{S}/ws_{p}/M15_broker.csv')
F = {}
for p in set(v[0] for v in REL.values()):
    m = pd.read_csv(m15(p), parse_dates=['time']).set_index('time')
    h1 = m.resample('1h').agg(dict(high='max', low='min', close='last')).dropna(); pc = h1.close.shift()
    atr = np.maximum(h1.high - h1.low, np.maximum((h1.high - pc).abs(), (h1.low - pc).abs())).rolling(14).mean()
    mv = (h1.close - h1.close.shift(24)) / atr; mv.index = mv.index + pd.Timedelta('1h')
    h4 = m.close.resample('4h').last().dropna(); ma = (h4 - h4.rolling(75).mean()); ma.index = ma.index + pd.Timedelta('4h')
    F[p] = (mv.dropna(), ma.dropna())
def at(s, t):
    i = s.index.searchsorted(t, 'right') - 1; return s.iloc[i] if i >= 0 else np.nan
rows = []
for sym, (rp, sg) in REL.items():
    mv, ma = F[rp]
    for ea, f in N.CORE:
        x = N.load(sym, f)
        if x is None: continue
        d = sg * x.side.to_numpy()
        x = x.assign(ea=ea, sym=sym, a_mv=np.sign([at(mv, t) for t in x.tt]) * d, a_ma=np.sign([at(ma, t) for t in x.tt]) * d)
        rows.append(x)
X = pd.concat(rows)
for c in ('a_ma', 'a_mv'):
    print(f'\n### {c}（関連市場が同じ向き=+1 / 逆=-1）平均R 前半/後半')
    g = X.groupby(['sym', c, 'half']).R.mean().unstack(['half']).unstack(c).round(2); print(g.to_string())
    w = X.groupby(['sym', 'ea', 'half', c]).R.mean().unstack(c); w = (w[1.0] - w[-1.0]).unstack('half')
    print(f'EA×銘柄ごとの差（同じ−逆）が前後半とも+ : {((w[1] > 0) & (w[2] > 0)).sum()} / 前後半とも- : {((w[1] < 0) & (w[2] < 0)).sum()} / ばらばら : {((w[1] > 0) != (w[2] > 0)).sum()}')
