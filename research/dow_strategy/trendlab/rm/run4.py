"""Return move v3 (2026-11-03, after the user's chart marks).
Same setup as run3 (H4 Dow turn level L, peak >= 1 ATR(H4), touch back to L >= 6 h later, level holds with tol 0.2 / 0.0 ATR(H4)).
New:
  prior H4 trend: bars and size (ATR(H4)) of the trend that the H4 turn ended (from the previous event of the same machine).
  triggers: D = first M15 provisional Dow turn to s after the touch (no near-level condition, only 'not run away' < 1.5 ATR(H4) beyond L);
            TL = first close beyond the correction line; F = first of D or TL; DTL = both (old).
  stops: LO (old), BK = wick of the M15 breakout bar (first M15 close beyond L inside the H4 turn bar) -/+ 0.1 ATR(H1),
         BKB = the farther of BK and the band edge (L -/+ 0.3 ATR(H4)) -/+ 0.1 ATR(H1).
Exits H1 (trail H1 swings from +1R) and M2 (trail M15 swings from +2R).
"""
import sys, pickle, bisect, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition.pivots import atr
sym = sys.argv[1]; TL_ = '/home/user/trendlab'
COST = {'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4, 'XAGUSD': 8e-4, 'US30': 1.5e-4, 'US500': 2e-4, 'JP225': 3e-4, 'BTCUSD': 8e-4}[sym]
F = pickle.load(open(f'{TL_}/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c)
C4 = list(F.C4); A4 = atr(F.h4); C1 = np.array(F.C1, dtype='datetime64[ns]'); A1 = F.A1
H4h, H4l = F.h4.h.to_numpy(), F.h4.l.to_numpy()
CL = T + np.timedelta64(15, 'm')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
H1P, P15 = arr(F.H1P), arr(F.P15)
turn = {1: np.array(sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == 'up')),
        -1: np.array(sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == 'down'))}
maj = sorted([e for e in F.R4['events'] if e.get('machine') == 'major' and e['action'] in ('REVERSAL', 'START', 'PROV_START')], key=lambda e: e['idx'])
prv = sorted([e for e in F.R4['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')], key=lambda e: e['idx'])
ev = []
for kind, E in (('MAJ', maj), ('PRV', prv)):
    for k, e in enumerate(E):
        if e.get('broken_price') is None or (kind == 'MAJ' and e['action'] != 'REVERSAL'): continue
        s = 1 if e['to'] == 'up' else -1
        p = next((E[j]['idx'] for j in range(k - 1, -1, -1) if E[j]['to'] != e['to']), None)
        if p is None: continue
        ev.append((C4[e['idx']], s, e['broken_price'], kind, e['idx'], p))

def a1_at(i):
    k = np.searchsorted(C1, CL[i], side='right') - 1; return A1[max(k, 0)]

def swings_after(kind, t0, t1):
    TT, KK, PV = P15; q0 = np.searchsorted(TT, t0, side='left'); q1 = np.searchsorted(TT, t1, side='right')
    return [(TT[q], PV[q]) for q in range(q0, q1) if KK[q] == kind]

def sim(e, s, sl, ex):
    risk = (o[e] - sl) * s; en = o[e]; on = False
    for j in range(e, min(e + 96 * 20, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        fav = ((h[j] - en) if s == 1 else (en - l[j])) / risk
        if fav >= (1 if ex == 'H1' else 2): on = True
        if on:
            TT, KK, PV = (H1P if ex == 'H1' else P15); q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(e + 96 * 20, n) - 1; return (c[j] - en) * s / risk, j

rows = []; busy = {}
for tol in (0.2, 0.0):
 for t4, s, L, kind, k4e, kprev in sorted(ev, key=lambda x: x[0]):
     k4 = bisect.bisect_right(C4, t4) - 1; a4 = A4[k4]
     if not np.isfinite(a4) or a4 <= 0: continue
     i0 = int(np.searchsorted(T, np.datetime64(t4)))
     if i0 >= n: continue
     # prior trend (the one this turn ended): from the previous opposite event to this one
     seg_h, seg_l = H4h[kprev:k4e + 1], H4l[kprev:k4e + 1]
     pre_bars = k4e - kprev; pre_size = (seg_h.max() - seg_l.min()) / a4
     # breakout bar: first M15 close beyond L inside the H4 turn bar (4 h before its close)
     ib0 = int(np.searchsorted(T, np.datetime64(t4) - np.timedelta64(4, 'h')))
     bk = next((i for i in range(ib0, i0) if (c[i] - L) * s > 0), None)
     if bk is None: continue
     bkw = l[bk] if s == 1 else h[bk]
     peak = 0.0; peak_i = None; touch = None; dead = False
     for i in range(i0, min(i0 + 96 * 10, n)):
         if s * (c[i] - L) < -tol * a4: dead = True; break
         ex_ = ((h[i] - L) if s == 1 else (L - l[i])) / a4
         if ex_ > peak: peak, peak_i = ex_, i
         if peak >= 1.0 and i > peak_i and ((l[i] <= L + 0.3 * a4) if s == 1 else (h[i] >= L - 0.3 * a4)) and (i - i0) >= 24:
             touch = i; break
     if dead or touch is None: continue
     pk_px = L + s * peak * a4
     tlow = (l[touch] if s == 1 else h[touch])
     trig = {}; lst = turn[s]; q = int(np.searchsorted(lst, touch)); got_d = got_tl = None
     for i in range(touch, min(touch + 192, n)):
         if s * (c[i] - L) < -tol * a4: break
         if s * (c[i] - L) > 1.5 * a4: break
         if got_d is None and q < len(lst) and lst[q] <= i: got_d = i
         if got_tl is None:
             sw = swings_after('hi' if s == 1 else 'lo', T[peak_i], CL[i])
             if sw:
                 t2, p2 = sw[-1]; i2 = int(np.searchsorted(T, t2))
                 if i2 > peak_i and (p2 - pk_px) * s < 0:
                     line = pk_px + (p2 - pk_px) / (i2 - peak_i) * (i - peak_i)
                     if (c[i] - line) * s > 0: got_tl = i
         if got_d == i and 'D' not in trig: trig['D'] = i
         if got_tl == i and 'TL' not in trig: trig['TL'] = i
         if (got_d is not None or got_tl is not None) and 'F' not in trig: trig['F'] = i
         if got_d is not None and got_tl is not None and 'DTL' not in trig: trig['DTL'] = i
         if len(trig) == 4: break
     for tg, i in trig.items():
         e = i + 1
         if e >= n: continue
         a1 = a1_at(i)
         lowx = (l[touch:i + 1].min() if s == 1 else h[touch:i + 1].max())
         band = L - s * 0.3 * a4
         far = min(bkw, band) if s == 1 else max(bkw, band)
         stops = {'LO': lowx - s * 0.2 * a1, 'BK': bkw - s * 0.1 * a1, 'BKB': far - s * 0.1 * a1}
         for stn, sl in stops.items():
             if (o[e] - sl) * s <= 0: continue
             for exn in ('H1', 'M2'):
                 key = (tol, kind, tg, stn, exn, s)
                 if busy.get(key, -1) >= e: continue
                 R, j = sim(e, s, sl, exn); risk = (o[e] - sl) * s; busy[key] = j
                 rows.append(dict(sym=sym, tol=tol, kind=kind, trig=tg, stop=stn, ex=exn, side=s, t=pd.Timestamp(T[e]), exit_t=pd.Timestamp(T[j]),
                                  R=R - COST / risk, peak=peak, pre_bars=pre_bars, pre_size=pre_size, L=L, sl=sl, t4=pd.Timestamp(t4),
                                  touch_t=pd.Timestamp(T[touch]), trig_t=pd.Timestamp(T[i]), h_touch=(touch - i0) / 4, h_trig=(i - touch) / 4,
                                  riskA=risk / a4, dist=(o[e] - L) * s / a4))
pd.DataFrame(rows).to_pickle(f'{TL_}/rm/r4_{sym}.pkl'); print(sym, len(rows), flush=True)
