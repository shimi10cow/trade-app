"""Split entry on the H4 return move (user, 2026-11-03): half at the M15 stochastic (ST), the other half at the M15 Dow turn (D).
Setups: run8 rows, provisional H4 turn, prior H4 trend >= 50 bars, level break <= 0.5 ATR(H4). Exit = trail M15 swings from +2R (M2).
Variants (R in units of the full 1R risk, each half risks 0.5):
  D    : full size at D (base)
  ST   : full size at ST
  SP   : half at ST, half at D (D added whether or not the first half is still open)
  SPX  : like SP, but while D has not come the ST half is closed at the next open when an M15 close breaks the level by > 0.5 ATR(H4)
         or when 48 h from the touch pass without D (the small exit)
"""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
sym = sys.argv[1]; stop = sys.argv[2] if len(sys.argv) > 2 else 'LO5'; TL_ = '/home/user/trendlab'
F = pickle.load(open(f'{TL_}/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c); CL = T + np.timedelta64(15, 'm')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
P15 = arr(F.P15)
d = pd.read_pickle(f'{TL_}/rm/r8_{sym}.pkl')
d = d[(d.kind == 'PRV') & (d.pre_bars >= 50) & (d.stop == stop) & (d.ex == 'M2') & (d.brk <= 0.5)]
cost_of = lambda r: r.R  # placeholder
def run(e, s, sl, cancel=None):
    """M2 trail; cancel = (L, a4, i_D or None, i_end): before i_D, close breaking L by > 0.5 a4 or reaching i_end -> exit next open."""
    risk = (o[e] - sl) * s; en = o[e]; on = False
    for j in range(e, min(e + 96 * 20, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        if cancel is not None:
            L, a4, iD, iend = cancel
            if iD is None or j < iD:
                if -s * (c[j] - L) > 0.5 * a4 or j >= iend:
                    k = min(j + 1, n - 1); return (o[k] - en) * s / risk, k
        if ((h[j] - en) if s == 1 else (en - l[j])) / risk >= 2: on = True
        if on:
            TT, KK, PV = P15; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(e + 96 * 20, n) - 1; return (c[j] - en) * s / risk, j
idx = lambda t: int(np.searchsorted(T, np.datetime64(t)))
rows = []
for key, g in d.groupby(['t4', 'side']):
    s = int(key[1]); D = g[g.trig == 'D']; ST = g[g.trig == 'ST']
    if not len(D) and not len(ST): continue
    D = D.iloc[0] if len(D) else None; ST = ST.iloc[0] if len(ST) else None
    base = ST if ST is not None else D
    a4 = base.riskA and ((idx(base.t) < n) and ((o[idx(base.t)] - base.sl) * s / base.riskA)); L = base.L
    cR = lambda r: r.R - (r.R_raw if 'R_raw' in r else 0)
    out = dict(sym=sym, t4=key[0], side=s, hasD=D is not None, hasST=ST is not None)
    # costs: stored R already has cost; reuse the cost per trade = stored R - re-simulated raw R
    def leg(r, cancel=None):
        e = idx(r.t); raw, _ = run(e, s, r.sl); cost = r.R - raw
        R, j = run(e, s, r.sl, cancel); return R + cost, pd.Timestamp(T[j]), r.t
    if D is not None:
        R, x, t0 = leg(D); out.update(D=R, D_t=t0, D_x=x)
    if ST is not None:
        R, x, t0 = leg(ST); out.update(ST=R, ST_t=t0, ST_x=x)
        iD = idx(D.trig_t) if (D is not None and D.trig_t > ST.trig_t) else (None if D is None else idx(ST.trig_t))
        iend = idx(pd.Timestamp(ST.touch_t) + pd.Timedelta('48h'))
        R2, x2, _ = leg(ST, (L, a4, iD, iend)); out.update(STX=R2, STX_x=x2)
    rows.append(out)
r = pd.DataFrame(rows)
r['SP'] = 0.5 * r.ST.fillna(0) + 0.5 * r.D.fillna(0)
r.loc[r.ST.isna() & r.D.isna(), 'SP'] = np.nan
r['SPX'] = 0.5 * r.STX.fillna(0) + 0.5 * r.D.fillna(0)
r.to_pickle(f'{TL_}/rm/sp_{sym}_{stop}.pkl'); print(sym, stop, len(r), flush=True)
