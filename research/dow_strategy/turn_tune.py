"""Tune the turn-follower J on the FIRST HALF only (2005-2015), check the second half (2016-2026) untouched.
Base: M15 provisional turn before the major turn, H4 provisional trend same, stop beyond the higher low + 0.3 ATR, H1 trail from +1R.
Knobs (one at a time, then the best two together): exit (h1 / hyb / m15), H1 condition, environment filters (notri, maxdev,
dside, range score), session."""
import sys, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import turn_ea as TE  # noqa: E402
X = TE.X; B = TE.B
BASEEV = TE.events('M15', 'same')
def h1filter(ev, mode):
    out = []
    for e in ev:
        k1 = bisect.bisect_right(B.C1, e['t']) - 1; d = 'up' if e['side'] == 1 else 'down'
        if mode == 'h1prov' and B.R1['prov_bars'][k1][0] != d: continue
        if mode == 'h1major' and B.R1['bars'][k1][0] != d: continue
        if mode == 'h1notagainst' and B.R1['bars'][k1][0] not in (d,) and B.R1['prov_bars'][k1][0] != d: continue
        if mode.startswith('hour'):
            h = (e['t'] - pd.Timedelta(minutes=15)).hour; lo, hi = map(int, mode[4:].split('_'))
            if not lo <= h < hi: continue
        out.append(e)
    return out
BASE = dict(trig='now', stop='ref', buf=0.3, exit='h1', act=1.0, win=1)
V = {'base': ({}, None), 'exit_hyb': (dict(exit='hyb', sw=2.0), None), 'exit_m15': (dict(exit='m15'), None),
     'notri': (dict(notri='H4'), None), 'maxdev3': (dict(maxdev=3), None), 'maxdev4': (dict(maxdev=4), None), 'dside': (dict(dside=0), None),
     'rs_T': (dict(env='T2', rs_lo=0.5), None), 'rs_R': (dict(env='R2', rs_hi=0.5), None),
     'h1prov': ({}, 'h1prov'), 'h1major': ({}, 'h1major'), 'h1notagainst': ({}, 'h1notagainst'),
     'hour0_10': ({}, 'hour0_10'), 'hour10_24': ({}, 'hour10_24'), 'buf0.6_act1.5': (dict(buf=0.6, act=1.5), None)}


def run1(k):
    cfg, f = V[k]; ev = h1filter(BASEEV, f) if f else BASEEV
    tr = X.run(ev, dict(BASE, **cfg)); tr.to_csv(TE.OUT / f'jt_{k}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    def st(m):
        rr = r[m]; w = rr > 0
        return len(rr), rr.sum(), rr[w].sum() / max(1e-9, -rr[~w].sum())
    a = st(y <= 2015); b = st(y >= 2016)
    eq = r[y <= 2015].cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min() if len(eq) else 0
    return dict(key=k, n1=a[0], R1=a[1], PF1=a[2], DD1=dd, n2=b[0], R2=b[1], PF2=b[2])


if __name__ == '__main__':
    with Pool(3) as p:
        rows = list(p.imap_unordered(run1, list(V)))
    D = pd.DataFrame(rows).sort_values('PF1', ascending=False); D.to_csv(TE.OUT / f'jt_summary_{sys.argv[1] if len(sys.argv) > 1 else "x"}.csv', index=False)
    pd.set_option('display.width', 200); print(D.round(2).to_string(index=False))
