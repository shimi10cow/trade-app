"""Raise the stop to new H4 swings before the trail starts (2026-11-04, user): after entry, when a confirmed H4 swing low (high for
sells) appears that is above the current stop and below the close, the stop moves to it (no buffer, like the M15 / H1 trails);
from the EA's own trail start, its own trail as now. Same entries / first stops as full/current.pkl, live Frames.
Variants: OWN (as now), H4 (H4 swings confirmed after the entry), H4ANY (any confirmed H4 swing, also older ones), H4BE (H4 swings
but never above the entry until the own trail starts)."""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
sym = sys.argv[1]; TL_ = '/home/user/trendlab'
F = pickle.load(open(f'{TL_}/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c); CL = T + np.timedelta64(15, 'm')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
PV = {'H1': arr(F.H1P), 'M15': arr(F.P15), 'H4': arr(F.H4P)}
COST = 1.2e-4
OWN = {'S@BTCUSD': ('H1', 2), 'T@US30': ('M15', 2), 'T2@EURUSD': ('M15', 2), 'DS@JP225': ('H1', 1.5), 'DS@US500': ('H1', 1.5), 'DS@XAUUSD': ('H1', 1.5), 'Q@XAGUSD': ('H4', 1)}
def last(tf, j, s, after=None):
    TT, KK, PP = PV[tf]; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
    while q >= 0 and KK[q] != want: q -= 1
    if q < 0 or (after is not None and TT[q] <= after): return None
    return PP[q]
def sim(e, s, en, sl, own, mode):
    risk = (en - sl) * s; best = 0.0; tf, act = own
    for j in range(e, min(e + 96 * 60, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        best = max(best, ((h[j] - en) if s == 1 else (en - l[j])) / risk)
        if best >= act:
            p = last(tf, j, s)
            if p is not None and (p - sl) * s > 0 and (p - c[j]) * s < 0: sl = p
        elif mode != 'OWN':
            p = last('H4', j, s, after=None if mode == 'H4ANY' else T[e])
            if p is not None and (p - sl) * s > 0 and (p - c[j]) * s < 0:
                if mode == 'H4BE' and (p - en) * s > 0: p = en if (en - sl) * s > 0 else None
                if p is not None: sl = p
    j = min(e + 96 * 60, n) - 1; return (c[j] - en) * s / risk, j
X = pd.read_pickle(f'{TL_}/full/current4.pkl') if False else pd.read_pickle(f'{TL_}/full/current.pkl')
X = X[(X.sym == sym) & ~X.key.isin(['A@EURUSD', 'R@EURUSD']) & ~X.key.str.startswith('M@')]
rows = []
for r in X.itertuples():
    s = int(r.side); e = int(np.searchsorted(T, np.datetime64(r.t)))
    if e >= n: continue
    tol = 1e-6 * max(1, abs(r.entry))
    if abs(o[e] - r.entry) > tol:
        if abs(c[e] - r.entry) <= tol: e += 1
        else: continue
    if e >= n: continue
    risk = (r.entry - r.sl0) * s
    if risk <= 0: continue
    own = OWN.get(r.key, ('H1', 1)); out = dict(key=r.key, sym=sym, t=r.t, side=s, R=r.R)
    for m in ('OWN', 'H4', 'H4ANY', 'H4BE'):
        R, j = sim(e, s, r.entry, r.sl0, own, m); out[m] = R - COST / risk; out['x_' + m] = pd.Timestamp(T[j])
    rows.append(out)
pd.DataFrame(rows).to_pickle(f'{TL_}/exit/h4_{sym}.pkl'); print(sym, len(rows), flush=True)
