"""Return move v2 (2026-11, user's picture): H4 Dow turn level -> price leaves it and builds a peak (space) -> comes back to the
level -> the level holds -> M15 trigger near the level. One symbol per run, full-history live Frames (cached).

Level L: the broken price of an H4 major reversal (MAJ) or of an H4 provisional turn (PRV); s = the new trend's side.
Peak: after the H4 bar closed, the farthest price beyond L on the trade side; a setup needs the peak >= dep x ATR(H4) (dep 1/1.5/2).
Touch: after the peak, an M15 bar comes back within 0.3 ATR(H4) of L, at least 6 h after the H4 turn, within 10 days.
Holds: cancelled when an M15 close goes beyond L against the trade by > 0.5 ATR(H4) (before the touch or before the trigger).
Trigger within 48 h of the touch while the close is within 1 ATR(H4) of L:
  D   = M15 provisional Dow turn to s
  TL  = M15 close beyond the pullback line from the peak through the latest lower M15 swing high (higher swing low for sells)
  DTL = the first bar where both have happened since the touch
Entry at the next M15 open. Stops: LO = lowest low since the touch - 0.2 ATR(H1) (mirror for sells); LV = L -/+ 0.5 ATR(H4).
Exits: H1 = trail confirmed H1 swings from +1R; M2 = trail confirmed M15 swings once +2R; PK = target at the peak (stop as is).
At most 20 days. One open position per (variant, side).
"""
import sys, pickle, bisect, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition.pivots import atr
sym = sys.argv[1]; TL_ = '/home/user/trendlab'
COST = {'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4, 'XAGUSD': 8e-4, 'US30': 1.5e-4, 'US500': 2e-4, 'JP225': 3e-4, 'BTCUSD': 8e-4}[sym]
F = pickle.load(open(f'{TL_}/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c)
C4 = list(F.C4); A4 = atr(F.h4); C1 = np.array(F.C1, dtype='datetime64[ns]'); A1 = F.A1
CL = T + np.timedelta64(15, 'm')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
H1P, P15 = arr(F.H1P), arr(F.P15)
turn = {1: np.array(sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == 'up')),
        -1: np.array(sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == 'down'))}
ev = [(C4[e['idx']], 1 if e['to'] == 'up' else -1, e['broken_price'], 'MAJ') for e in F.R4['events']
      if e.get('machine') == 'major' and e['action'] == 'REVERSAL' and e.get('broken_price') is not None]
ev += [(C4[e['idx']], 1 if e['to'] == 'up' else -1, e.get('broken_price'), 'PRV') for e in F.R4['prov_events']
       if e['action'] in ('REVERSAL', 'PROV_START') and e.get('broken_price') is not None]

def a1_at(i):
    k = np.searchsorted(C1, CL[i], side='right') - 1; return A1[max(k, 0)]

def swings_after(kind, t0, t1):
    TT, KK, PV = P15; q0 = np.searchsorted(TT, t0, side='left'); q1 = np.searchsorted(TT, t1, side='right')
    return [(TT[q], PV[q]) for q in range(q0, q1) if KK[q] == kind]

def sim(e, s, sl, ex, tp):
    risk = (o[e] - sl) * s; en = o[e]; on = False
    for j in range(e, min(e + 96 * 20, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        if ex == 'PK' and ((h[j] >= tp) if s == 1 else (l[j] <= tp)): return (tp - en) * s / risk, j
        fav = ((h[j] - en) if s == 1 else (en - l[j])) / risk
        if ex == 'H1' and fav >= 1: on = True
        if ex == 'M2' and fav >= 2: on = True
        if on:
            TT, KK, PV = (H1P if ex == 'H1' else P15); q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(e + 96 * 20, n) - 1; return (c[j] - en) * s / risk, j

rows = []; busy = {}
for t4, s, L, kind in sorted(ev, key=lambda x: x[0]):
    k4 = bisect.bisect_right(C4, t4) - 1; a4 = A4[k4]
    if not np.isfinite(a4) or a4 <= 0: continue
    i0 = int(np.searchsorted(T, np.datetime64(t4)))
    if i0 >= n: continue
    peak = 0.0; peak_i = None; touch = None; dead = False
    for i in range(i0, min(i0 + 96 * 10, n)):
        if s * (c[i] - L) < -0.5 * a4: dead = True; break
        ex_ = ((h[i] - L) if s == 1 else (L - l[i])) / a4
        if ex_ > peak: peak, peak_i = ex_, i
        if peak >= 1.0 and i > peak_i and ((l[i] <= L + 0.3 * a4) if s == 1 else (h[i] >= L - 0.3 * a4)) and (i - i0) >= 24:
            touch = i; break
    if dead or touch is None: continue
    pk_px = L + s * peak * a4
    trig = {}
    lst = turn[s]; q = np.searchsorted(lst, touch)
    got_d = got_tl = None
    for i in range(touch, min(touch + 192, n)):
        if s * (c[i] - L) < -0.5 * a4: break
        near = s * (c[i] - L) <= 1.0 * a4
        if got_d is None and q < len(lst) and lst[q] <= i and lst[q] >= touch: got_d = i
        while q < len(lst) and lst[q] < touch: q += 1
        if got_tl is None:
            sw = swings_after('hi' if s == 1 else 'lo', T[peak_i], CL[i])
            if sw:
                t2, p2 = sw[-1]; i2 = int(np.searchsorted(T, t2))
                if i2 > peak_i and (p2 - pk_px) * s < 0:
                    line = pk_px + (p2 - pk_px) / (i2 - peak_i) * (i - peak_i)
                    if (c[i] - line) * s > 0: got_tl = i
        if near:
            if got_d == i and 'D' not in trig: trig['D'] = i
            if got_tl == i and 'TL' not in trig: trig['TL'] = i
            if got_d is not None and got_tl is not None and 'DTL' not in trig: trig['DTL'] = i
        if len(trig) == 3: break
    for tg, i in trig.items():
        e = i + 1
        if e >= n: continue
        lowx = (l[touch:i + 1].min() if s == 1 else h[touch:i + 1].max())
        stops = {'LO': lowx - s * 0.2 * a1_at(i), 'LV': L - s * 0.5 * a4}
        for stn, sl in stops.items():
            if (o[e] - sl) * s <= 0: continue
            for exn in ('H1', 'M2', 'PK'):
                if exn == 'PK' and (pk_px - o[e]) * s <= 0: continue
                key = (kind, tg, stn, exn, s)
                if busy.get(key, -1) >= e: continue
                R, j = sim(e, s, sl, exn, pk_px); risk = (o[e] - sl) * s; busy[key] = j
                rows.append(dict(sym=sym, kind=kind, trig=tg, stop=stn, ex=exn, side=s, t=pd.Timestamp(T[e]), exit_t=pd.Timestamp(T[j]),
                                 R=R - COST / risk, peak=peak, L=L, pk_px=pk_px, sl=sl, t4=pd.Timestamp(t4), peak_t=pd.Timestamp(T[peak_i]), touch_t=pd.Timestamp(T[touch]), trig_t=pd.Timestamp(T[i]), h_touch=(touch - i0) / 4, h_trig=(i - touch) / 4, riskA=risk / a4))
pd.DataFrame(rows).to_pickle(f'{TL_}/rm/r_{sym}.pkl'); print(sym, len(rows), flush=True)
