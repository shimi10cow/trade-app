"""'Recognise the correction / long range and trade it short' (2026-11): H1 Dow entries in the direction of the daily Dow,
labelled with the weekly / daily context, several early exits. One symbol per run, full-history live Frames (cached).

Entries at the H1 close (next M15 open):
  H1M  : H1 major Dow trend turns to s
  H1P4 : H1 provisional trend turns to s while the H4 provisional trend is already s
Direction s must equal the daily Dow (major DM or provisional DP, both recorded) -> the move being traded is the daily one.
Stop: the H1 protected level (major for H1M, provisional for H1P4) -/+ 0.3 ATR(H1); 0.2..4 ATR(H1) wide, else skipped.
Exits: T1 = trail confirmed H1 swings from +1R, at most 10 days; M1 = trail confirmed M15 swings from +1R, at most 5 days;
       DX = close when the daily provisional trend turns against s (the daily move is over), at most 10 days.
One position per side and exit kind. Context at entry: WM, WP, DM, DP, W_in, D_in (regime/dow_states.pkl).
"""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
sym = sys.argv[1]; TL = '/home/user/trendlab'
COST = {'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4, 'XAGUSD': 8e-4, 'US30': 1.5e-4, 'US500': 2e-4, 'JP225': 3e-4, 'BTCUSD': 8e-4}[sym]
F = pickle.load(open(f'{TL}/live_frames_{sym}.pkl', 'rb')); ST = pd.read_pickle(f'{TL}/regime/dow_states.pkl')[sym]
SG = {'up': 1, 'down': -1}
T15 = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c)
C1 = np.array(F.C1, dtype='datetime64[ns]'); A1 = F.A1
b1 = [(SG.get(b[0], 0), b[1]) for b in F.R1['bars']]; p1 = [(SG.get(b[0], 0), b[1]) for b in F.R1['prov_bars']]
C4 = np.array(F.C4, dtype='datetime64[ns]'); p4 = np.array([SG.get(b[0], 0) for b in F.R4['prov_bars']])
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
H1P, P15 = arr(F.H1P), arr(F.P15)
send = ST.index.to_numpy(); DPv = ST.DP.to_numpy()

def ctx_at(t):
    k = np.searchsorted(send, t, side='right') - 1
    return None if k < 0 else ST.iloc[k]

def dp_at(t):
    k = np.searchsorted(send, t, side='right') - 1
    return DPv[k] if k >= 0 else 0

def run(i0, s, en, sl, kind):
    risk = abs(en - sl); on = False; maxb = 96 * (5 if kind == 'M1' else 10)
    TT, KK, PV = (P15 if kind == 'M1' else H1P)
    for j in range(i0, min(i0 + maxb, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return (min(sl, o[j]) if s == 1 else max(sl, o[j]) - 0) , j
        if kind == 'DX':
            if dp_at(T15[j] + np.timedelta64(15, 'm')) == -s: return c[j], j
            continue
        fav = ((h[j] - en) if s == 1 else (en - l[j]))
        if not on and fav >= risk: on = True
        if on:
            q = np.searchsorted(TT, T15[j] + np.timedelta64(15, 'm'), side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(i0 + maxb, n) - 1; return c[j], j

rows = []; busy = {}
for k in range(1, len(C1)):
    for trig in ('H1M', 'H1P4'):
        cur, prev = (b1[k][0], b1[k - 1][0]) if trig == 'H1M' else (p1[k][0], p1[k - 1][0])
        if cur == 0 or cur == prev: continue
        s = cur; ref = b1[k][1] if trig == 'H1M' else p1[k][1]
        if ref is None or not np.isfinite(ref): continue
        if trig == 'H1P4':
            k4 = np.searchsorted(C4, C1[k], side='right') - 1
            if k4 < 0 or p4[k4] != s: continue
        cx = ctx_at(C1[k])
        if cx is None or not (cx.DM == s or cx.DP == s): continue
        i0 = int(np.searchsorted(T15, C1[k]))
        if i0 >= n: continue
        en = o[i0]; sl = ref - s * 0.3 * A1[k]; risk = (en - sl) * s
        if not (0.2 * A1[k] <= risk <= 4 * A1[k]): continue
        for kind in ('T1', 'M1', 'DX'):
            key = (trig, kind, s)
            if busy.get(key, -1) >= i0: continue
            xp, j = run(i0, s, en, sl, kind); busy[key] = j
            rows.append(dict(sym=sym, trig=trig, ex=kind, side=s, t=pd.Timestamp(T15[i0]), exit_t=pd.Timestamp(T15[j]), R=(xp - en) * s / risk - COST / risk,
                             WM=cx.WM, WP=cx.WP, DM=cx.DM, DP=cx.DP, W_in=bool(cx.W_in), D_in=bool(cx.D_in), riskA=risk / A1[k]))
pd.DataFrame(rows).to_pickle(f'{TL}/regime/ce_{sym}.pkl'); print(sym, len(rows), flush=True)
