"""Return move on H1 (2026-11-03, user): H1 Dow turn level L (major reversal MAJ / provisional turn PRV) after an H1 trend,
peak >= 1 ATR(H1) beyond L, touch back within 0.3 ATR(H1) at least 1 h after the turn (within 3 days), the level holds
(close not beyond L by > tol ATR(H1)), M15 trigger within 12 h of the touch (no more than 1.5 ATR(H1) beyond L):
D = first M15 provisional Dow turn to s, TL = close beyond the correction line, F = the first of the two.
Stops: LO = lowest low since the touch - 0.1 ATR(H1); BK = wick of the M15 breakout bar - 0.1 ATR(H1).
Exits: M1 / M15 / M2 = trail confirmed M15 swings from +1 / +1.5 / +2R; H1 = trail confirmed H1 swings from +1R.
Recorded: prior H1 trend bars and size, H4 provisional trend side (h4 = +1 same as the trade), D1 Dow side not kept.
"""
import sys, pickle, bisect, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
sym = sys.argv[1]; TL_ = '/home/user/trendlab'
COST = {'GBPUSD': 1.5e-4, 'AUDUSD': 1.3e-4, 'USDCAD': 2e-4, 'USDCHF': 2e-4, 'EURJPY': 2e-4, 'AUDJPY': 2.5e-4, 'CADJPY': 3e-4, 'CHFJPY': 3e-4,
        'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4}[sym]
F = pickle.load(open(f'{TL_}/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c)
C1 = np.array(F.C1, dtype='datetime64[ns]'); A1 = F.A1; H1h, H1l = F.h1.h.to_numpy(), F.h1.l.to_numpy()
C4 = np.array(F.C4, dtype='datetime64[ns]')
CL = T + np.timedelta64(15, 'm')
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
H1P, P15 = arr(F.H1P), arr(F.P15)
turn = {1: np.array(sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == 'up')),
        -1: np.array(sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == 'down'))}
p4 = sorted([e for e in F.R4['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')], key=lambda e: e['idx'])
p4t = np.array([C4[e['idx']] for e in p4]); p4s = np.array([1 if e['to'] == 'up' else -1 for e in p4])
maj = sorted([e for e in F.R1['events'] if e.get('machine') == 'major' and e['action'] in ('REVERSAL', 'START', 'PROV_START')], key=lambda e: e['idx'])
prv = sorted([e for e in F.R1['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')], key=lambda e: e['idx'])
ev = []
for kind, E in (('MAJ', maj), ('PRV', prv)):
    for k, e in enumerate(E):
        if e.get('broken_price') is None or (kind == 'MAJ' and e['action'] != 'REVERSAL'): continue
        p = next((E[j]['idx'] for j in range(k - 1, -1, -1) if E[j]['to'] != e['to']), None)
        if p is None: continue
        ev.append((C1[e['idx']], 1 if e['to'] == 'up' else -1, e['broken_price'], kind, e['idx'], p))

def swings_after(kind, t0, t1):
    TT, KK, PV = P15; q0 = np.searchsorted(TT, t0, side='left'); q1 = np.searchsorted(TT, t1, side='right')
    return [(TT[q], PV[q]) for q in range(q0, q1) if KK[q] == kind]

def sim(e, s, sl, piv, start, tp=None):
    risk = (o[e] - sl) * s; en = o[e]; on = False
    for j in range(e, min(e + 96 * 10, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        if tp is not None and ((h[j] >= tp) if s == 1 else (l[j] <= tp)): return (tp - en) * s / risk, j
        if piv is None: continue
        if ((h[j] - en) if s == 1 else (en - l[j])) / risk >= start: on = True
        if on:
            TT, KK, PV = piv; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(e + 96 * 10, n) - 1; return (c[j] - en) * s / risk, j
EXITS = {'M1': (P15, 1), 'M2': (P15, 2), 'H1': (H1P, 1), 'PK': (None, 0), 'PK2': (None, 0)}
rows = []; busy = {}
for tol in (1.0,):
 for t1, s, L, kind, k1e, kprev in sorted(ev, key=lambda x: x[0]):
     a1 = A1[k1e]
     if not np.isfinite(a1) or a1 <= 0: continue
     i0 = int(np.searchsorted(T, t1))
     if i0 >= n: continue
     pre_bars = k1e - kprev; pre_size = (H1h[kprev:k1e + 1].max() - H1l[kprev:k1e + 1].min()) / a1
     q4 = np.searchsorted(p4t, t1, side='right') - 1; h4 = int(p4s[q4] == s) if q4 >= 0 else 0
     bk = next((i for i in range(max(i0 - 4, 0), i0) if (c[i] - L) * s > 0), None)
     if bk is None: continue
     bkw = l[bk] if s == 1 else h[bk]
     peak = 0.0; peak_i = None; touch = None; dead = False
     for i in range(i0, min(i0 + 96 * 3, n)):
         if s * (c[i] - L) < -tol * a1: dead = True; break
         ex_ = ((h[i] - L) if s == 1 else (L - l[i])) / a1
         if ex_ > peak: peak, peak_i = ex_, i
         if peak >= 1.0 and i > peak_i and ((l[i] <= L + 0.3 * a1) if s == 1 else (h[i] >= L - 0.3 * a1)) and (i - i0) >= 4:
             touch = i; break
     if dead or touch is None: continue
     pk_px = L + s * peak * a1
     trig = {}; lst = turn[s]; q = int(np.searchsorted(lst, touch)); got_d = got_tl = None; brk = {}; mx = 0.0
     for i in range(touch, min(touch + 48, n)):
         if s * (c[i] - L) < -tol * a1: break
         if s * (c[i] - L) > 2.5 * a1: break
         mx = max(mx, -s * (c[i] - L) / a1)
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
         for kk in trig: brk.setdefault(kk, mx)
         if len(trig) == 3: break
     for tg, i in trig.items():
         e = i + 1
         if e >= n: continue
         lowx = (l[touch:i + 1].min() if s == 1 else h[touch:i + 1].max())
         stops = {'LO': lowx - s * 0.1 * a1, 'LO3': lowx - s * 0.3 * a1, 'BK': bkw - s * 0.1 * a1, 'LV1': L - s * 1.0 * a1}
         for stn, sl in stops.items():
             if (o[e] - sl) * s <= 0: continue
             risk = (o[e] - sl) * s
             for exn, (piv, st) in EXITS.items():
                 key = (tol, kind, tg, stn, exn, s)
                 if busy.get(key, -1) >= e: continue
                 tp = pk_px if exn == 'PK' else (L + s * 2 * (pk_px - L) * s * s if exn == 'PK2' else None)
                 if tp is not None and (tp - o[e]) * s <= 0: continue
                 R, j = sim(e, s, sl, piv, st, tp); busy[key] = j
                 rows.append(dict(sym=sym, tol=tol, kind=kind, trig=tg, stop=stn, ex=exn, side=s, t=pd.Timestamp(T[e]), exit_t=pd.Timestamp(T[j]),
                                  R=R - COST / risk, peak=peak, pre_bars=pre_bars, pre_size=pre_size, h4=h4, L=L, sl=sl, t1=pd.Timestamp(t1),
                                  h_touch=(touch - i0) / 4, brk=brk[tg], tpR=((tp - o[e]) * s / risk) if tp is not None else np.nan, h_trig=(i - touch) / 4, riskA=risk / a1))
pd.DataFrame(rows).to_pickle(f'{TL_}/rm/r7_{sym}.pkl'); print(sym, len(rows), flush=True)
