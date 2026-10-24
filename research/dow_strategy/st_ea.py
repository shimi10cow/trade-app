"""Short-term EA (2026-10-21): M15 Dow turn at an H1 level, in the H1 trend.
Setup (H1 bar close, buy shown): H1 major trend up and the H1 bar's low came within `near` x ATR(H1) of
  [ma]  H1 SMA75, or [sw] the last confirmed H1 swing high that was broken (support from former resistance), or [both]
and closed above it. Trigger: M15 provisional turn up within `win` h. Stop: the M15 turn swing + buf x ATR(H1).
Exit short-term: 'm15' (M15 swing trail from +act R) or fixed target tp R. Cost 1.2 pip. First/second half reported."""
import sys, bisect, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'st'; OUT.mkdir(parents=True, exist_ok=True)
h1 = B.h1; c1 = h1.c.to_numpy(float); l1 = h1.l.to_numpy(float); hh1 = h1.h.to_numpy(float); A1 = B.A1
S75 = pd.Series(c1).rolling(75).mean().to_numpy()
maj = [b[0] for b in B.R1['bars']]
PV = sorted((e['available_idx'], e['kind'], e['price']) for e in B.R1['pivot_events'] if e.get('action', 'confirm') == 'confirm')
PA = [p[0] for p in PV]
def last_swing(k, kind):
    j = bisect.bisect_right(PA, k) - 1
    while j >= 0 and PV[j][1] != kind: j -= 1
    return PV[j][2] if j >= 0 else None
def events(level='both', near=0.3, win=6):
    ev = []
    for k in range(200, len(c1)):
        d = maj[k]
        if d not in ('up', 'down'): continue
        s = 1 if d == 'up' else -1; a = A1[k]; ext = l1[k] if s == 1 else hh1[k]
        lv = []
        if level in ('ma', 'both'): lv.append(S75[k])
        if level in ('sw', 'both'):
            v = last_swing(k, 'hi' if s == 1 else 'lo')
            if v is not None and s * (c1[k] - v) > 0: lv.append(v)
        for v in lv:
            if np.isfinite(v) and s * (ext - v) <= near * a and s * (c1[k] - v) > 0:
                ev.append(dict(t=B.C1[k], side=s, tag='st', win=win)); break
    return ev
GRID = dict(level=('ma', 'sw', 'both'), near=(0.3,), exit=(('m15', 1.0), ('m15', 0.5), ('tp', 1.5), ('tp', 2.0), ('h1', 1.0)))
def run1(c):
    ev = events(c['level'], c['near'])
    ex, v = c['exit']
    cfg = dict(trig='dow', stop='m15turn', buf=0.5, win=6)
    if ex == 'tp':
        cfg.update(exit='m15', act=99.0)
    else:
        cfg.update(exit=ex, act=v)
    tr = X.run(ev, cfg)
    if ex == 'tp':   # apply fixed target post-hoc on M15 path: exit at tp if reached before the original exit
        R = []
        for x in tr.itertuples():
            i0 = X.M15T.searchsorted(x.t); ie = X.M15T.searchsorted(x.exit_t)
            tp = x.entry + x.side * v * x.risk; hit = None
            for i in range(i0, min(ie + 1, X.N)):
                if (B.l[i] <= x.sl0) if x.side == 1 else (B.h[i] >= x.sl0): break
                if (B.h[i] >= tp) if x.side == 1 else (B.l[i] <= tp): hit = i; break
            R.append(v - B.COST / x.risk if hit is not None else x.R)
        tr['R'] = R
    key = f"{c['level']}_{ex}{v}"; tr.to_csv(OUT / f'st_{key}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    pf = lambda x: x[x > 0].sum() / max(1e-9, -x[x <= 0].sum())
    return f"{key:12s} n={len(r):5d} {r.sum():+7.1f}R PF{pf(r):.2f} 勝率{(r > 0).mean():.0%} | 前半 {r[y <= 2015].sum():+.1f}R PF{pf(r[y <= 2015]):.2f} | 後半 {r[y >= 2016].sum():+.1f}R PF{pf(r[y >= 2016]):.2f} | SL{tr.risk.median() / 1e-4:.0f}p 保有{((tr.exit_t - tr.t).dt.total_seconds() / 3600).median():.0f}h"
if __name__ == '__main__':
    C = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    with Pool(2) as p:
        for s in p.imap_unordered(run1, C): print(s, flush=True)
