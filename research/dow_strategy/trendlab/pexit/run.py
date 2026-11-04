"""P exits (2026-11-04, user: P leans on a few big trades - can the exit spread it?). P's live trades (current rules) on 5 symbols;
same entry (signal bar close) and first stop; exits re-simulated with confirmed H1 swings (like P: trail from +1R, stop below the
close). Variants (R in units of the full position):
  BASE   : trail H1 swings from +1R (P now)
  HALF1 / HALF15 / HALF2 / HALF3 : half closed at +1 / +1.5 / +2 / +3R, the rest as BASE
  THIRD  : a third at +1R, a third at +2R, the rest as BASE
  BE1    : stop to entry at +1R, then as BASE
  HALF2BE: half at +2R and the stop of the rest to entry, then as BASE
"""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.eas import nt as NT
sym = sys.argv[1]
path = f'/home/user/trendlab/idx/frames_{sym}.pkl' if sym in ('US500', 'US100') else f'/home/user/trendlab/live_frames_{sym}.pkl'
F = pickle.load(open(path, 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c); CL = T + np.timedelta64(15, 'm')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
H1P = arr(F.H1P)
cost = NT.COST.get(sym, 1.2e-4)
tr = NT.run(F, sym, seed=False)['trades']; tr['t'] = pd.to_datetime(tr.t); tr = tr[tr.t >= ('2017-07-01' if sym in ('US500', 'US100') else '2005-06-01')]
def leg(e, s, en, sl, tp=None, be=None):
    risk = (en - sl) * s; on = False; moved = False
    for j in range(e, min(e + 96 * 60, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk
        fav = ((h[j] - en) if s == 1 else (en - l[j])) / risk
        if tp is not None and fav >= tp: return tp
        if be is not None and not moved and fav >= be: sl = en if (en - sl) * s > 0 else sl; moved = True
        if fav >= 1: on = True
        if on:
            TT, KK, PV = H1P; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(e + 96 * 60, n) - 1; return (c[j] - en) * s / risk
rows = []
for r in tr.itertuples():
    s = int(r.side); e = int(np.searchsorted(T, np.datetime64(r.t))) + 1
    if e >= n: continue
    en, sl = r.entry, r.sl0; risk = (en - sl) * s
    if risk <= 0: continue
    k = cost / risk; base = leg(e, s, en, sl)
    v = dict(BASE=base, BE1=leg(e, s, en, sl, be=1))
    for nm, x in (('HALF1', 1), ('HALF15', 1.5), ('HALF2', 2), ('HALF3', 3)):
        v[nm] = 0.5 * leg(e, s, en, sl, tp=x) + 0.5 * base
    v['THIRD'] = (leg(e, s, en, sl, tp=1) + leg(e, s, en, sl, tp=2) + base) / 3
    v['HALF2BE'] = 0.5 * leg(e, s, en, sl, tp=2) + 0.5 * leg(e, s, en, sl, be=2)
    rows.append(dict(sym=sym, t=r.t, side=s, R_live=r.R, **{a: b - k for a, b in v.items()}))
pd.DataFrame(rows).to_pickle(f'/home/user/trendlab/pexit/p_{sym}.pkl'); print(sym, len(rows), flush=True)
