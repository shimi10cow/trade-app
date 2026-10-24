"""Zone counter-move EA on M5 bars (2026-10-23, user: compare M5 vs M15 Dow-turn entries, stop beyond the zone vs at the
entry's own turn, several exits, and look at the MA).
Setup: H4 / D1 zone touch (zone_ea.touches). Trigger within 12h, zone not closed through:
   'm5'  = M5 provisional turn in the bounce direction (enter at that M5 close)
   'm15' = M15 provisional turn (enter at that M15 close)
Stop:  'zone'  = zone far edge - 0.3 ATR(H1)
       'turn'  = last confirmed swing of the trigger timeframe (M5 or M15) - 0.3 ATR(that TF); never wider than 'zone'
Exit:  'tp1.5','tp2','tp3' fixed target; 'be2' = stop to entry at +1R, target 3R; 'm15tr' = M15 swing trail from +1R;
       'h1tr' = H1 swing trail from +1R. Time limit 5 days.
MA context saved per trade (decided afterwards on the first half only):
   ma1 = H1 SMA75 slope in the bounce direction (+1 / -1), ma4 = same for H4 SMA75,
   conf = SMA75 (H1 or H4) inside the zone +- 0.5 ATR(H1) at the touch (MA and line overlap).
Writes results/zone/ZL_<tf>_<trig>_<stop>_<exit>.csv"""
import sys, itertools, os
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zone_ea as Z  # noqa: E402
import m5_base as MB  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
B = Z.B
m5, R5 = MB.get()
T5 = pd.DatetimeIndex(m5.t); H, L, C = (m5[z].to_numpy(float) for z in 'hlc'); A5 = atr(m5); N = len(T5)
CL5 = T5 + pd.Timedelta('5min')
def turns(R, close):
    return {d: np.array(sorted(close[e['idx']] for e in R['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d), dtype='datetime64[ns]') for d in ('up', 'down')}
TURN = {'m5': turns(R5, CL5), 'm15': turns(B.R15, pd.DatetimeIndex(Z.X.CL15))}
def pivots(R, close):
    P = sorted((close[e['available_idx']], e['kind'], e['price']) for e in R['pivot_events'])
    return np.array([p[0] for p in P], dtype='datetime64[ns]'), np.array([p[1] for p in P]), np.array([p[2] for p in P], float)
PIV = {'m5': pivots(R5, CL5), 'm15': pivots(B.R15, pd.DatetimeIndex(Z.X.CL15)), 'h1': pivots(B.R1, pd.DatetimeIndex(B.C1))}
A15 = atr(B.m15); T15C = np.array(Z.X.CL15, dtype='datetime64[ns]')
A1T = np.array(B.C1, dtype='datetime64[ns]'); A1 = np.asarray(B.A1, float)
h1c = pd.Series(B.h1.c.to_numpy(float), index=pd.DatetimeIndex(B.C1)); ma1 = h1c.rolling(75).mean()
h4c = pd.Series(B.h4.c.to_numpy(float), index=pd.DatetimeIndex(B.C4)); ma4 = h4c.rolling(75).mean()


def last_swing(tf, t, kind):
    PT, PK, PP = PIV[tf]; k = np.searchsorted(PT, np.datetime64(t), side='right') - 1
    while k >= 0 and PK[k] != kind: k -= 1
    return PP[k] if k >= 0 else None


def asof(s, t):
    i = s.index.searchsorted(t, 'right') - 1
    return s.iloc[i] if i >= 0 else np.nan


def ctx(e):
    t, s = e['t'], e['side']
    a1 = A1[max(np.searchsorted(A1T, np.datetime64(t), 'right') - 1, 0)]
    m1, m1p = asof(ma1, t), asof(ma1, t - pd.Timedelta('10h')); m4, m4p = asof(ma4, t), asof(ma4, t - pd.Timedelta('40h'))
    lo, hi = (e['ref'], e['ref'] + 1e9) if s == 1 else (-1e9, e['ref'])
    zt, zb = (e.get('top', np.nan), e.get('bot', np.nan))
    conf = any(np.isfinite(m) and (min(zt, zb) - 0.5 * a1) <= m <= (max(zt, zb) + 0.5 * a1) for m in (m1, m4))
    return dict(ma1=int(np.sign(s * (m1 - m1p))) if np.isfinite(m1p) else 0, ma4=int(np.sign(s * (m4 - m4p))) if np.isfinite(m4p) else 0, conf=int(conf), a1=a1)


def run(c):
    tf, trig, stop, ex = c
    out = []; busy = {1: np.datetime64('1900-01-01'), -1: np.datetime64('1900-01-01')}
    for e in TEV[tf]:
        s = e['side']; t0 = np.datetime64(e['t'])
        if t0 <= busy[s]: continue
        arr = TURN[trig]['up' if s == 1 else 'down']; k = np.searchsorted(arr, t0, 'right')
        if k >= len(arr) or arr[k] > t0 + np.timedelta64(12, 'h'): continue
        te = arr[k]; j = np.searchsorted(CL5, te, 'right') - 1      # M5 bar closing at/just before the trigger
        j0 = np.searchsorted(CL5, t0, 'left')
        if j < j0 or j >= N - 2: continue
        if (s == 1 and (C[j0:j + 1] < e['ref']).any()) or (s == -1 and (C[j0:j + 1] > e['ref']).any()): continue
        cx = CTX[id(e)]; zst = e['ref'] - s * 0.3 * cx['a1']; st = zst
        if stop == 'turn':
            sw = last_swing(trig, te, 'lo' if s == 1 else 'hi')
            if sw is not None:
                a = A5[j] if trig == 'm5' else A15[max(np.searchsorted(T15C, te, 'right') - 1, 0)]
                cand = sw - s * 0.3 * a
                if s * (cand - zst) > 0: st = cand
        en = C[j]; risk = s * (en - st)
        if risk <= 3 * B.PIP or s * (en - e['ref']) <= 0: continue
        tp = {'tp1.5': 1.5, 'tp2': 2, 'tp3': 3, 'be2': 3}.get(ex); trail = None if ex.startswith(('tp', 'be')) else ex[:-2]
        end = min(j + 1 + 288 * 5, N - 1); xp, xj = C[end], end; on = False; sl = st
        for i in range(j + 1, end + 1):
            if (L[i] <= sl) if s == 1 else (H[i] >= sl): xp, xj = sl, i; break
            if tp and ((H[i] >= en + s * tp * risk) if s == 1 else (L[i] <= en + s * tp * risk)): xp, xj = en + s * tp * risk, i; break
            fav = (H[i] - en) if s == 1 else (en - L[i])
            if fav >= risk:
                if ex == 'be2': sl = max(sl, en) if s == 1 else min(sl, en)
                on = True
            if trail and on:
                v = last_swing(trail, CL5[i], 'lo' if s == 1 else 'hi')
                if v is not None and ((v < C[i]) if s == 1 else (v > C[i])):
                    sl = max(sl, v) if s == 1 else min(sl, v)
        busy[s] = np.datetime64(CL5[xj])
        out.append(dict(t=CL5[j], exit_t=CL5[xj], side=s, entry=en, risk=risk, exit=xp, tag=e['tag'], ma1=cx['ma1'], ma4=cx['ma4'], conf=cx['conf'],
                        R=s * (xp - en) / risk - B.COST / risk))
    tr = pd.DataFrame(out); name = f'ZL_{tf}_{trig}_{stop}_{ex}'
    if len(tr): tr.to_csv(Z.OUT / f'{name}.csv', index=False)
    return name, len(tr), round(tr.R.sum(), 1) if len(tr) else 0


TEV = Z.TEV
CTX = {id(e): ctx(e) for tf in TEV for e in TEV[tf]}
if __name__ == '__main__':
    G = list(itertools.product(('H4', 'D1'), ('m5', 'm15'), ('zone', 'turn'), ('tp1.5', 'tp2', 'tp3', 'be2', 'm15tr', 'h1tr')))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for r in p.imap_unordered(run, G): print(*r, flush=True)
