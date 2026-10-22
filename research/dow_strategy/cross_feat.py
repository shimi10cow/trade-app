"""Cycle 4 features (2026-10-22):
 usd_cons  : does the OTHER USD pairs' last-24h move agree with the USD direction implied by the trade? (mean of signed moves in ATR(H1))
             EURUSD buy = USD weak; USDJPY buy = USD strong; GBPUSD buy = USD weak; gold buy = USD weak (assumed)
 jpy_cons  : same for JPY (USDJPY, EURJPY)
 stop_atr  : stop distance / ATR(H1)
 rn_room   : room (in ATR(H1)) to the next round level (FX: 100 pips; JPY pairs: 1 yen; gold/BTC: skipped) in the trade direction"""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
M15 = {'EURUSD': f'{S}/EURUSD_M15_long_broker.csv'} | {p: f'{S}/ws_{p}/M15_broker.csv' for p in ('USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD')}
T = pd.read_pickle(f'{S}/feat/all_trades_hold.pkl')
H = {}
for p, f in M15.items():
    m = pd.read_csv(f, parse_dates=['time']).set_index('time')
    h1 = m.resample('1h', label='left', closed='left').agg(dict(high='max', low='min', close='last')).dropna()
    pc = h1.close.shift(); tr = np.maximum(h1.high - h1.low, np.maximum((h1.high - pc).abs(), (h1.low - pc).abs()))
    h1['atr'] = tr.rolling(14).mean(); h1['mv'] = (h1.close - h1.close.shift(24)) / h1.atr
    h1.index = h1.index + pd.Timedelta('1h'); H[p] = h1
USD = {'EURUSD': -1, 'GBPUSD': -1, 'USDJPY': 1, 'XAUUSD': -1}   # +1 = pair up means USD strong
JPY = {'USDJPY': -1, 'EURJPY': -1}                               # pair up means JPY weak -> -1 for JPY strength
def at(p, t):
    h = H[p]; i = h.index.searchsorted(t, 'right') - 1
    return h.iloc[i] if i >= 0 else None
out = []
for x in T.itertuples():
    r = {}
    me = at(x.pair, x.tt)
    if me is None: out.append(r); continue
    r['stop_atr'] = x.risk / (me.atr / (100 if x.pair in ('USDJPY',) else 1)) if me.atr > 0 else np.nan
    for nm, D in (('usd_cons', USD), ('jpy_cons', JPY)):
        if x.pair in D:
            want = D[x.pair] * x.side   # +1 = trade implies currency strength
            v = [D[q] * at(q, x.tt).mv * want for q in D if q != x.pair and at(q, x.tt) is not None]
            r[nm] = np.nanmean(v) if v else np.nan
    if x.pair in ('EURUSD', 'GBPUSD', 'USDJPY', 'EURJPY'):
        step = 0.01  # 100 pips (JPY pairs are /100 in trade units)
        nxt = (np.floor(x.entry / step) + (1 if x.side == 1 else 0)) * step
        r['rn_room'] = abs(nxt - x.entry) / (me.atr / (100 if x.pair == 'USDJPY' else 1))
    out.append(r)
F = pd.DataFrame(out, index=T.index); F.to_pickle(f'{S}/feat/cross_feat.pkl'); print(F.describe().round(2).to_string())
