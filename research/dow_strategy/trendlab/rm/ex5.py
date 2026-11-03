"""More exits on run4 trades (same entries/stops): PK target at the H4 peak; M1/M15 trail from +1R/+1.5R; H2 = H1 trail from +2R;
PKH = half at the peak, rest trails H1 from +1R; TM = M2 but close after 3 days."""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
sym = sys.argv[1]; F = pickle.load(open(f'/home/user/trendlab/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c); CL = T + np.timedelta64(15, 'm')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
H1P, P15 = arr(F.H1P), arr(F.P15)
d = pd.read_pickle(f'r4_{sym}.pkl'); d = d[d.ex == 'M2'].copy()
COST = (d.R.iloc[0] * 0)  # cost re-applied from the stored difference below
def sim(e, s, sl, piv, start, tp=None, maxbars=96 * 20):
    risk = (o[e] - sl) * s; en = o[e]; on = False
    for j in range(e, min(e + maxbars, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk
        if tp is not None and ((h[j] >= tp) if s == 1 else (l[j] <= tp)): return (tp - en) * s / risk
        if ((h[j] - en) if s == 1 else (en - l[j])) / risk >= start: on = True
        if on:
            TT, KK, PV = piv; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(e + maxbars, n) - 1; return (c[j] - en) * s / risk
rows = []
for r in d.itertuples():
    e = int(np.searchsorted(T, np.datetime64(r.t))); s = r.side; risk = (o[e] - r.sl) * s; cost = r.R - sim(e, s, r.sl, P15, 2)
    a4 = risk / r.riskA; pk = r.L + s * r.peak * a4
    res = dict(PK=sim(e, s, r.sl, P15, 1e9, pk) if (pk - o[e]) * s > 0 else np.nan, M1=sim(e, s, r.sl, P15, 1), M15=sim(e, s, r.sl, P15, 1.5),
               H2=sim(e, s, r.sl, H1P, 2), TM=sim(e, s, r.sl, P15, 2, maxbars=96 * 3))
    res['PKH'] = 0.5 * res['PK'] + 0.5 * sim(e, s, r.sl, H1P, 1) if np.isfinite(res['PK']) else np.nan
    for k, v in res.items():
        x = r._asdict(); x.pop('Index'); x.update(ex=k, R=v + cost); rows.append(x)
pd.DataFrame(rows).to_pickle(f'r5_{sym}.pkl'); print(sym, len(rows), flush=True)
