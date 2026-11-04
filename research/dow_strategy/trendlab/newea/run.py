"""New EA ideas that should work across markets (2026-11-04, user: all three). One simple engine, broker-time data, 5 markets.
A trend on a higher frame, a stochastic (14,3,5) pullback on a lower frame:
  A0 control (P-like): trend = H1 SMA20 vs SMA75, pullback on M15, the first 2 pullbacks of each trend, trail H1 swings
  A1 idea 1        : trend = H4 SMA20 vs SMA75, pullback on H1, the first 2 pullbacks, trail H4 swings
  A2 idea 2        : trend = H1 major Dow trend, pullback on M15, the first 2 pullbacks, trail H1 swings
  A3 idea 3        : trend = weekly major Dow trend, pullback on H4, every pullback, trail H4 swings
Signal (buys): K went under 20, then K over D and K over 20 at a bar close of the pullback frame. Entry at the next M15 open.
Stop: the pullback low (lowest low since K went under 20) - 0.2 ATR14 of the pullback frame. Trail from +1R to the last
confirmed swing of the trail frame below the close; at most 60 days. One open position per side. Costs per symbol.
Usage: python run.py EURUSD  -> newea/n_{sym}.pkl
"""
import pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition import dow_trend
sym = sys.argv[1]
COST = {'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4, 'US500': 2e-4, 'US100': 2e-4}[sym]
IDX = sym in ('US500', 'US100')
F = pickle.load(open(f'/home/user/trendlab/idx/frames_{sym}.pkl' if IDX else f'/home/user/trendlab/tz/frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c); CL = T + np.timedelta64(15, 'm')
START = np.datetime64('2017-07-01' if IDX else '2005-06-01')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
PIV = {'H1': arr(F.H1P), 'H4': arr(F.H4P)}
def tf(name):
    if name == 'M15': return dict(cl=CL, o=o, h=h, l=l, c=c)
    df = F.h1 if name == 'H1' else F.h4; cl = np.array(F.C1 if name == 'H1' else F.C4, dtype='datetime64[ns]')
    return dict(cl=cl, o=df.o.to_numpy(float), h=df.h.to_numpy(float), l=df.l.to_numpy(float), c=df.c.to_numpy(float))
def stoch(d):
    hh = pd.Series(d['h']).rolling(14).max(); ll = pd.Series(d['l']).rolling(14).min()
    k = (100 * (pd.Series(d['c']) - ll) / (hh - ll)).rolling(3).mean(); return k.to_numpy(), k.rolling(5).mean().to_numpy()
def atr(d):
    pc = np.r_[np.nan, d['c'][:-1]]; tr = np.nanmax(np.vstack([d['h'] - d['l'], np.abs(d['h'] - pc), np.abs(d['l'] - pc)]), axis=0)
    return pd.Series(tr).rolling(14).mean().to_numpy()
# trends as (close times, value) on the trend frame
def ma_trend(name):
    d = tf(name); s20 = pd.Series(d['c']).rolling(20).mean().to_numpy(); s75 = pd.Series(d['c']).rolling(75).mean().to_numpy()
    return d['cl'], np.sign(np.nan_to_num(s20 - s75))
def dow1():
    v = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in F.R1['bars']]); return np.array(F.C1, dtype='datetime64[ns]'), v
def weekly():
    w1 = getattr(F, 'W1', None)
    if w1 is None:
        mb = F.m15_all.set_index('t'); w1 = mb.resample('W-MON', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    R = dow_trend.run(w1[['t', 'o', 'h', 'l', 'c']].reset_index(drop=True), 'W1')
    end = (pd.to_datetime(w1.t) + pd.Timedelta(days=7)).to_numpy(); v = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['bars']])
    return end, v
def sim(e, s, sl, piv):
    en = o[e]; risk = (en - sl) * s; on = False
    for j in range(e, min(e + 96 * 60, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        if ((h[j] - en) if s == 1 else (en - l[j])) / risk >= 1: on = True
        if on:
            TT, KK, PV = piv; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(e + 96 * 60, n) - 1; return (c[j] - en) * s / risk, j
IDEAS = {'A0': ('M15', ma_trend('H1'), 2, 'H1'), 'A1': ('H1', ma_trend('H4'), 2, 'H4'), 'A2': ('M15', dow1(), 2, 'H1'), 'A3': ('H4', weekly(), 99, 'H4')}
rows = []
for name, (lo, (tcl, tv), maxpb, trail) in IDEAS.items():
    d = tf(lo); K, D = stoch(d); A = atr(d); cl = d['cl']; nb = len(cl)
    kk = np.searchsorted(tcl, cl, side='right') - 1                      # last closed trend bar at each pullback-frame close
    reg = np.where(kk >= 0, tv[np.clip(kk, 0, None)], 0)
    busy = {1: np.datetime64('1970-01-01'), -1: np.datetime64('1970-01-01')}
    cur = 0; cnt = 0; zone = {1: None, -1: None}
    for i in range(1, nb):
        if reg[i] != cur: cur = reg[i]; cnt = 0; zone = {1: None, -1: None}
        if cur == 0 or not np.isfinite(K[i]) or not np.isfinite(D[i]) or not np.isfinite(A[i]): continue
        s = int(cur)
        if (K[i] < 20) if s == 1 else (K[i] > 80):
            if zone[s] is None: zone[s] = i
            continue
        if zone[s] is None: continue
        if not (((K[i] > D[i]) and K[i] > 20) if s == 1 else ((K[i] < D[i]) and K[i] < 80)): continue
        z = zone[s]; zone[s] = None; cnt += 1
        if cnt > maxpb or cl[i] < START: continue
        e = int(np.searchsorted(T, cl[i]))
        if e >= n or T[e] <= busy[s]: continue
        ref = d['l'][z:i + 1].min() if s == 1 else d['h'][z:i + 1].max(); sl = ref - s * 0.2 * A[i]
        if (o[e] - sl) * s <= 0: continue
        R, j = sim(e, s, sl, PIV[trail]); busy[s] = T[j]
        rows.append(dict(sym=sym, idea=name, t=pd.Timestamp(T[e]), exit_t=pd.Timestamp(T[j]), side=s, pb=cnt, R=R - COST / ((o[e] - sl) * s)))
    print(sym, name, sum(r['idea'] == name for r in rows), flush=True)
pd.DataFrame(rows).to_pickle(f'/home/user/trendlab/newea/n_{sym}.pkl')
