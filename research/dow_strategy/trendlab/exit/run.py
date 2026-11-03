"""Exit review for every live EA (2026-11-03, user order 1): same entries and initial stops (full/current.pkl), exits re-simulated
on the live Frames (research price space). Variants: trail confirmed swings of TF from +k R:
  H1_0.5 H1_1 H1_1.5 H1_2 | M15_1 M15_2 M15_3 | H4_1 H4_2 | HYB = H1 from +1R, M15 once +3R | BE = stop to entry at +1R, H1 from +2R.
At most 60 days. Cost = F.COST / risk (same for every variant). M (daily RSI2) is left out (its own daily exit).
"""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
sym = sys.argv[1]; TL_ = '/home/user/trendlab'
F = pickle.load(open(f'{TL_}/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c); CL = T + np.timedelta64(15, 'm')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
PV = {'H1': arr(F.H1P), 'M15': arr(F.P15), 'H4': arr(F.H4P)}
COST = float(F.COST) if np.ndim(F.COST) == 0 else float(np.asarray(F.COST).ravel()[0])
VAR = {'H1_0.5': [('H1', 0.5)], 'H1_1': [('H1', 1)], 'H1_1.5': [('H1', 1.5)], 'H1_2': [('H1', 2)], 'M15_1': [('M15', 1)], 'M15_2': [('M15', 2)],
       'M15_3': [('M15', 3)], 'H4_1': [('H4', 1)], 'H4_2': [('H4', 2)], 'HYB': [('H1', 1), ('M15', 3)], 'BE': [('BE', 1), ('H1', 2)]}
def last_swing(tf, j, s):
    TT, KK, PP = PV[tf]; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
    while q >= 0 and KK[q] != want: q -= 1
    return PP[q] if q >= 0 else None
def sim(e, s, en, sl, steps):
    risk = (en - sl) * s; best = 0.0
    for j in range(e, min(e + 96 * 60, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        best = max(best, ((h[j] - en) if s == 1 else (en - l[j])) / risk)
        tf = None
        for t_, k in steps:
            if best >= k: tf = t_
        if tf == 'BE':
            if (en - sl) * s > 0: sl = en
        elif tf is not None:
            p = last_swing(tf, j, s)
            if p is not None and (p - sl) * s > 0 and (p - c[j]) * s < 0: sl = p
    j = min(e + 96 * 60, n) - 1; return (c[j] - en) * s / risk, j
X = pd.read_pickle(f'{TL_}/full/current.pkl'); X = X[(X.sym == sym) & (X.key != 'A@EURUSD') & ~X.key.str.startswith('M@')]
rows = []
for r in X.itertuples():
    s = int(r.side); e = int(np.searchsorted(T, np.datetime64(r.t)))
    if e >= n: continue
    tol = 1e-6 * max(1, abs(r.entry))
    if abs(o[e] - r.entry) > tol:
        if abs(c[e] - r.entry) <= tol: e += 1          # entry at the signal bar's close (P, T, T2)
        else: continue
    if e >= n: continue
    risk = (r.entry - r.sl0) * s
    if risk <= 0: continue
    out = dict(key=r.key, sym=sym, t=r.t, side=s, R=r.R, exit_t=r.exit_t, w=r.w, mult=r.mult, risk=risk)
    for nm, st in VAR.items():
        R, j = sim(e, s, r.entry, r.sl0, st); out[nm] = R - COST / risk; out['x_' + nm] = pd.Timestamp(T[j])
    rows.append(out)
pd.DataFrame(rows).to_pickle(f'{TL_}/exit/e_{sym}.pkl'); print(sym, len(X), len(rows), 'COST', COST, flush=True)
