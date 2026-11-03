"""L (trendline bounce) taken apart (2026-11-03, user order 2). Touches from the live L.line_touches (H4 and H1 lines, touches 3-6),
with the line features; entries / stops / exits varied. Every variant is simulated on its own (one open per variant and side).
Entries: T  = first M15 provisional turn in the line direction within 24 h (now), next M15 open
         N  = next M15 open right after the touch bar closes (at the line)
         S  = M15 stochastic (14,3,5) back over 20 (under 80) with K over D, after having been under 20 (over 80), within 24 h
Stops:   W10 / W05 / W03 = the M15 turn swing (for N / S: the lowest low since the touch) -/+ 1.0 / 0.5 / 0.3 ATR(H1), min 10 pips
         LN = the line value at entry -/+ 0.5 ATR of the line TF
Exits:   H1_1 / H1_2 = trail confirmed H1 swings from +1R / +2R. Max 60 days.
Kept per touch: tf, n, angle, depth, trend agree, daily side value (H4 close vs SMA1200 / ATR), H4 triangle (env notri), dist of
entry from the line (ATR(H1)), hours from touch to entry.
"""
import sys, pickle, bisect, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.eas import l as LL
from mt5_ea.live.env import Env
from env_recognition.pivots import atr
sym = sys.argv[1]; TL_ = '/home/user/trendlab'
COST = {'GBPUSD': 1.5e-4, 'AUDUSD': 1.3e-4, 'USDCAD': 2e-4, 'USDCHF': 2e-4, 'EURJPY': 2e-4, 'AUDJPY': 2.5e-4, 'CADJPY': 3e-4, 'CHFJPY': 3e-4,
        'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4}[sym]
F = pickle.load(open(f'{TL_}/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c); CL = T + np.timedelta64(15, 'm'); M15T = F.M15T
C1 = np.array(F.C1, dtype='datetime64[ns]'); A1 = F.A1; A4 = atr(F.h4); PIP = F.PIP
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
H1P = arr(F.H1P)
env = Env(F.m15_all)
_c4 = pd.Series(F.h4.c.to_numpy(float)); SMA1200 = _c4.rolling(1200).mean().to_numpy()
def sd(t, s): k = bisect.bisect_right(F.C4, t) - 1; return s * (_c4[k] - SMA1200[k]) / A4[k]
_ll = pd.Series(l).rolling(14).min(); _hh = pd.Series(h).rolling(14).max()
KK = (100 * (pd.Series(c) - _ll) / (_hh - _ll)).rolling(3).mean(); DD_ = KK.rolling(5).mean(); KK = KK.to_numpy(); DD_ = DD_.to_numpy()
prov = [e for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
turns = {'up': np.array(sorted(e['idx'] for e in prov if e['to'] == 'up')), 'down': np.array(sorted(e['idx'] for e in prov if e['to'] == 'down'))}
FR = {'H4': (F.h4, F.R4, F.C4, A4), 'H1': (F.h1, F.R1, F.C1, F.A1)}
def sim(e, s, sl, act):
    en = o[e]; risk = (en - sl) * s; on = False
    for j in range(e, min(e + 96 * 60, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        if ((h[j] - en) if s == 1 else (en - l[j])) / risk >= act: on = True
        if on:
            TT, KK_, PV = H1P; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK_[q] != want: q -= 1
            if q >= 0:
                v = PV[q] - s * PIP
                if (v - sl) * s > 0 and (v - c[j]) * s < 0: sl = v
    j = min(e + 96 * 60, n) - 1; return (c[j] - en) * s / risk, j
rows = []; busy = {}
touches = []
for tf in ('H4', 'H1'):
    df, R, C, A = FR[tf]; Ctf = list(C)
    for e in LL.line_touches(df, R, C, A, tf):
        if e['kind'] != 'touch' or not (3 <= e['n'] <= 6) or e['depth'] is None: continue
        touches.append((e, tf, A))
touches.sort(key=lambda x: x[0]['t'])
for e, tf, A in touches:
    s = 1 if e['d'] == 'up' else -1; t0 = pd.Timestamp(e['t'])
    i0 = int(M15T.searchsorted(t0)); i1 = int(M15T.searchsorted(t0 + pd.Timedelta(hours=24)))
    if i0 >= n - 2 or t0 < F.START: continue
    k1 = bisect.bisect_right(F.C1, t0) - 1; a1 = A1[k1]
    ktf = bisect.bisect_right(list(FR[tf][2]), t0) - 1 if False else None
    # line value per M15 bar: v at the touch bar + slope per tf bar (slope = angle * A[ia] signed)
    tf_h = 4 if tf == 'H4' else 1
    slope_px_per_h = s * e['angle'] * A[e['ia']] / tf_h
    line_at = lambda i: e['v'] + slope_px_per_h * ((T[i] - np.datetime64(t0)) / np.timedelta64(1, 'h'))
    feat = dict(sym=sym, tf=tf, n=e['n'], angle=e['angle'], depth=e['depth'], agree=int(e['trend'] == e['d']), side=s, touch_t=t0,
                sd=sd(t0, s), tri=int(not env.ok({'maxdev': None, 'notri': 'H4'}, t0, s)))
    ents = {}
    lst = turns[e['d']]; q = int(np.searchsorted(lst, i0))
    if q < len(lst) and lst[q] < i1:
        it = int(lst[q]); sw = F.R15['prov_bars'][it][1]
        if sw is not None: ents['T'] = (it, sw)
    ents['N'] = (i0, None)
    zone = False
    for i in range(i0, min(i1, n - 1)):
        if (KK[i] < 20) if s == 1 else (KK[i] > 80): zone = True
        if zone and (((KK[i] > DD_[i]) and KK[i] > 20) if s == 1 else ((KK[i] < DD_[i]) and KK[i] < 80)): ents['S'] = (i, None); break
    for en_name, (i, sw) in ents.items():
        e1 = i + 1
        if e1 >= n: continue
        ref = sw if sw is not None else (l[i0:i + 1].min() if s == 1 else h[i0:i + 1].max())
        lv = line_at(e1); atf = A[e['ia']]
        stops = {'W10': ref - s * 1.0 * a1, 'W05': ref - s * 0.5 * a1, 'W03': ref - s * 0.3 * a1, 'LN': lv - s * 0.5 * atf}
        for stn, sl in stops.items():
            if (o[e1] - sl) * s < 10 * PIP: sl = o[e1] - s * 10 * PIP
            for act in (1, 2):
                key = (tf, en_name, stn, act, s, e['n'] >= 3)
                if busy.get(key, -1) >= e1: continue
                R, j = sim(e1, s, sl, act); risk = (o[e1] - sl) * s; busy[key] = j
                rows.append(dict(feat, entry=en_name, stop=stn, ex=f'H1_{act}', t=pd.Timestamp(T[e1]), exit_t=pd.Timestamp(T[j]), R=R - COST / risk,
                                 riskA=risk / a1, dist=(o[e1] - lv) * s / a1, h_ent=(e1 - i0) / 4))
pd.DataFrame(rows).to_pickle(f'{TL_}/lab_l/l_{sym}.pkl'); print(sym, len(touches), len(rows), flush=True)
