"""Pattern 3 of the zone counter-move idea (2026-10-23): H4 / D1 zone touch (zone_ea.touches) -> M5 provisional turn in
the bounce direction within 12h (zone not closed through) -> enter at that M5 close.
Stop: 'zone' = zone far edge - buf x ATR(H1), or 'm5' = last confirmed M5 swing - 0.5 ATR(M5) (tighter, never beyond the
zone stop). Exit: fixed target tp R or the stop; time limit 5 days (exit at close). One position per side.
Needs the M5 Dow cache (m5_base.get, M5_SYM). Writes results/zone/Z5_<tf>_<stop>_<tp>.csv"""
import sys, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import zone_ea as Z  # noqa: E402  (zones / touches on this workspace)
import m5_base as MB  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
B = Z.B
m5, R5 = MB.get()
T5 = pd.DatetimeIndex(m5.t); O, H, L, C = (m5[z].to_numpy(float) for z in 'ohlc'); A5 = atr(m5); N = len(T5)
CL5 = T5 + pd.Timedelta('5min')
TURN = {d: np.array(sorted(e['idx'] for e in R5['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d)) for d in ('up', 'down')}
PV = sorted((e['available_idx'], e['kind'], e['price']) for e in R5['pivot_events'] if e.get('action', 'confirm') == 'confirm')
PA = np.array([p[0] for p in PV]); PK = np.array([p[1] for p in PV]); PP = np.array([p[2] for p in PV])
A1T = pd.DatetimeIndex(B.C1); A1 = np.asarray(B.A1, float)


def last_swing(i, kind):
    k = np.searchsorted(PA, i, side='right') - 1
    while k >= 0 and PK[k] != kind: k -= 1
    return PP[k] if k >= 0 else None


def run(tf, stop, tp, buf=0.3):
    out = []; busy = {1: -1, -1: -1}
    for e in Z.TEV[tf]:
        s = e['side']; j0 = CL5.searchsorted(e['t'], 'left')
        if j0 >= N - 2 or j0 <= busy[s]: continue
        arr = TURN['up' if s == 1 else 'down']; k = np.searchsorted(arr, j0)
        if k >= len(arr) or arr[k] >= j0 + 144: continue
        j = arr[k]
        if (s == 1 and (C[j0:j + 1] < e['ref']).any()) or (s == -1 and (C[j0:j + 1] > e['ref']).any()): continue
        k1 = A1T.searchsorted(CL5[j], 'right') - 1
        zst = e['ref'] - s * buf * A1[max(k1, 0)]; st = zst
        if stop == 'm5':
            sw = last_swing(j, 'lo' if s == 1 else 'hi')
            if sw is not None:
                cand = sw - s * 0.5 * A5[j]
                if s * (cand - zst) > 0: st = cand
        en = C[j]; risk = s * (en - st)
        if risk <= 3 * B.PIP: continue
        tgt = en + s * tp * risk; end = min(j + 1 + 288 * 5, N - 1); xp, xj = C[end], end
        for i in range(j + 1, end + 1):
            if (L[i] <= st) if s == 1 else (H[i] >= st): xp, xj = st, i; break
            if (H[i] >= tgt) if s == 1 else (L[i] <= tgt): xp, xj = tgt, i; break
        busy[s] = xj
        out.append(dict(t=CL5[j], exit_t=CL5[xj], side=s, entry=en, risk=risk, exit=xp, tag=e['tag'],
                        R=s * (xp - en) / risk - B.COST / risk))
    tr = pd.DataFrame(out)
    if len(tr): tr.to_csv(Z.OUT / f'Z5_{tf}_{stop}_tp{tp}.csv', index=False)
    return tr


if __name__ == '__main__':
    for tf, stop, tp in itertools.product(('H4', 'D1'), ('zone', 'm5'), (1.5, 2, 3)):
        tr = run(tf, stop, tp)
        y = tr.t.dt.year if len(tr) else pd.Series(dtype=int)
        a = tr[y <= 2015].R; b = tr[y >= 2016].R
        print(f'Z5 {tf} {stop} tp{tp}: {len(tr)} 回 前半 {a.sum():+.1f}R / 後半 {b.sum():+.1f}R', flush=True)
