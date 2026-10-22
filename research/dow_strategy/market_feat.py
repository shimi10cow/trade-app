"""Market-condition features at each trade's entry (known before entry; uses bars closed before the entry time).
vol_h1   ATR14(H1) / its median over the past 1000 H1 bars        (is it a busy or quiet period?)
vol_d1   ATR14(D1) / its median over the past 250 days
d1_gap   side * (close - SMA50 D1) / ATR(D1)                       (is price stretched along the daily trend?)
d1_slope side * (SMA50 D1 now - 10 days ago) / ATR(D1)            (daily trend strength in trade direction)
d1_200   side * sign(close - SMA200 D1)
rng20    side-signed position in the past 20-day range: 1 = at the edge the trade goes toward, 0 = at the other edge
room_pd  side * (prev-day high (buy) / low (sell) - close) / ATR(D1)  (room to the previous day's extreme)
er24     efficiency ratio of the last 24 H1 closes (1 = straight line, 0 = choppy)
dir24    side * (close - close 24 H1 ago) / ATR(H1)
hour, wday, month (broker time)"""
import sys
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'} | {p: f'{S}/ws_{p}/M15_broker.csv' for p in ('USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD')}
def atr(d, n=14):
    pc = d.c.shift(); tr = np.maximum(d.h - d.l, np.maximum((d.h - pc).abs(), (d.l - pc).abs())); return tr.rolling(n).mean()
def bars(m, rule):
    d = m.resample(rule, label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna()
    d['end'] = d.index + pd.Timedelta(rule); return d
def feats(pair, tr):
    m = pd.read_csv(M15[pair], parse_dates=['time']).set_index('time'); m.columns = ['o', 'h', 'l', 'c']
    h1 = bars(m, '1h'); d1 = bars(m, '1D'); d1 = d1[d1.h > d1.l]
    h1['atr'] = atr(h1); h1['atrm'] = h1.atr.rolling(1000, min_periods=300).median()
    h1['er'] = (h1.c - h1.c.shift(24)).abs() / h1.c.diff().abs().rolling(24).sum(); h1['c24'] = h1.c.shift(24)
    d1['atr'] = atr(d1); d1['atrm'] = d1.atr.rolling(250, min_periods=100).median()
    d1['s50'] = d1.c.rolling(50).mean(); d1['s50b'] = d1.s50.shift(10); d1['s200'] = d1.c.rolling(200).mean()
    d1['hi20'] = d1.h.rolling(20).max(); d1['lo20'] = d1.l.rolling(20).min()
    he = h1.end.to_numpy(); de = d1.end.to_numpy(); m15e = (m.index + pd.Timedelta('15min')).to_numpy(); mc = m.c.to_numpy()
    out = []
    for t, s in zip(tr.tt.to_numpy(), tr.side.to_numpy()):
        i = np.searchsorted(he, t, 'right') - 1; j = np.searchsorted(de, t, 'right') - 1; k = np.searchsorted(m15e, t, 'right') - 1
        if i < 0 or j < 0 or k < 0: out.append({}); continue
        H = h1.iloc[i]; D = d1.iloc[j]; c = mc[k]
        rng = D.hi20 - D.lo20; pos = (c - D.lo20) / rng if rng > 0 else np.nan
        out.append(dict(vol_h1=H.atr / H.atrm, vol_d1=D.atr / D.atrm, d1_gap=s * (c - D.s50) / D.atr, d1_slope=s * (D.s50 - D.s50b) / D.atr,
                        d1_200=s * np.sign(c - D.s200), rng20=pos if s == 1 else 1 - pos,
                        room_pd=s * ((D.h if s == 1 else D.l) - c) / D.atr, er24=H.er, dir24=s * (c - H.c24) / H.atr))
    f = pd.DataFrame(out, index=tr.index)
    f['hour'] = tr.tt.dt.hour; f['wday'] = tr.tt.dt.weekday; f['month'] = tr.tt.dt.month
    return f
if __name__ == '__main__':
    T = pd.read_pickle(sys.argv[1]); pair = sys.argv[2]
    tr = T[T.pair == pair]; f = feats(pair, tr); f.to_pickle(f'{S}/feat/mkt_{pair}.pkl'); print(pair, len(f), f.notna().mean().round(2).to_dict())
