"""Setup generators for the 'trend-following' sub-rules (2026-10-20). Each returns events for ea_core.run:
dict(t=<time known>, side=+1/-1, tag=str, ref=<structure price for the 'ref' stop>, [win=hours]).
All causal: H4 values come from H4 bars closed at the M15 bar's close; touches are tested on closed M15 bars.

  fib_pullback      : H4 trend leg (protected swing -> highest high since the protection was set); price pulls back
                      to 38.2 / 50 / 61.8 % of the leg (within tol x ATR H4) without breaking the protected level
  protected_retest  : price comes back near the H4 protected level (押し安値/戻り高値 only)
  box_counter       : user idea - H4 turns (closes through the protected high) but a higher confirmed high sits just
                      above (within k x ATR): sell when price reaches that higher high (mirror for buys)
  w_trend_end       : good W (speed / shape / prior run, retest_ea 'wq') - the W is the reversal itself
"""
import bisect, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
from env_recognition.pivots import atr  # noqa: E402

A4 = atr(B.h4); H4H = B.h4.h.to_numpy(float); H4L = B.h4.l.to_numpy(float)
K4 = np.searchsorted(np.array(B.C4, dtype='datetime64[ns]'), X.CL15.to_numpy(dtype='datetime64[ns]'), side='right') - 1


def _leg_extremes():
    """Per H4 bar: (trend, prot, leg extreme since the protection was set) using closed H4 bars only."""
    out = []; prev = None; ext = None
    for k, (tr, prot) in enumerate(B.R4['bars']):
        if tr is None or prot is None:
            out.append((None, None, None)); prev = None; continue
        if prev != (tr, prot):
            ext = H4H[k] if tr == 'up' else H4L[k]; prev = (tr, prot)
        else:
            ext = max(ext, H4H[k]) if tr == 'up' else min(ext, H4L[k])
        out.append((tr, prot, ext))
    return out


LEG = _leg_extremes()


def fib_pullback(levels=(0.382, 0.5, 0.618), tol=0.15, min_leg=3.0, win=24):
    ev = []; done = set()
    for i in range(X.N):
        k = K4[i]
        if k < 0:
            continue
        tr, prot, ext = LEG[k]
        if tr is None:
            continue
        s = 1 if tr == 'up' else -1; leg = s * (ext - prot)
        if leg < min_leg * A4[k]:
            continue
        if (B.c[i] <= prot) if s == 1 else (B.c[i] >= prot):
            continue
        for f in levels:
            key = (prot, round(ext, 5), f)
            if key in done:
                continue
            lv = ext - s * f * leg; band = tol * A4[k]
            if (B.l[i] <= lv + band) if s == 1 else (B.h[i] >= lv - band):
                done.add(key)
                ev.append(dict(t=X.CL15[i], side=s, tag=f'fib{int(f * 1000)}', ref=prot, win=win, level=lv,
                               leg_atr=leg / A4[k]))
    return ev


def protected_retest(band=0.5, win=24):
    ev = []; armed = {1: True, -1: True}
    for i in range(X.N):
        k = K4[i]
        if k < 0:
            continue
        tr, prot = B.R4['bars'][k]
        if tr is None or prot is None:
            continue
        s = 1 if tr == 'up' else -1; bd = band * A4[k]
        if (B.l[i] > prot + 2 * bd) if s == 1 else (B.h[i] < prot - 2 * bd):
            armed[s] = True
        near = (B.l[i] <= prot + bd) if s == 1 else (B.h[i] >= prot - bd)
        if near and armed[s] and s * (B.c[i] - prot) > 0:
            armed[s] = False
            ev.append(dict(t=X.CL15[i], side=s, tag='prot', ref=prot, win=win))
    return ev


def box_counter(k_atr=1.5, tol=0.2, look=120, win=72):
    """After an H4 major reversal, the nearest confirmed opposite-side extreme just beyond the broken level."""
    piv = []                                               # (available_idx, kind, price, idx) using each confirmation
    for e in B.R4['pivot_events']:
        piv.append((e['available_idx'], e['kind'], e['price'], e['idx']))
    piv.sort()
    pav = [p[0] for p in piv]
    ev = []
    for e in B.R4['events']:
        if e.get('machine') != 'major' or e['action'] != 'REVERSAL':
            continue
        k = e['idx']; up = e['to'] == 'up'
        lvl = e['broken_price']                            # the protected level that was closed through
        kind = 'hi' if up else 'lo'
        cand = [p for p in piv[:bisect.bisect_right(pav, k)] if p[1] == kind and k - look <= p[3] < k]
        A = A4[k]
        cand = [p for p in cand if ((0 < p[2] - lvl <= k_atr * A) if up else (0 < lvl - p[2] <= k_atr * A))]
        if not cand:
            continue
        q = min(cand, key=lambda p: abs(p[2] - lvl))[2]
        s = -1 if up else 1                                  # trade against the fresh reversal, at the extreme beyond
        i0 = X.CL15.searchsorted(B.C4[k]); i1 = X.CL15.searchsorted(B.C4[k] + pd.Timedelta(hours=win))
        for i in range(i0, min(i1, X.N)):
            if (B.c[i] > q) if up else (B.c[i] < q):
                break                                      # closed beyond the higher high: idea is void
            if (B.h[i] >= q - tol * A) if up else (B.l[i] <= q + tol * A):
                ev.append(dict(t=X.CL15[i], side=s, tag='box', ref=q, win=24)); break
    return ev


def w_trend_end(tf='H4'):
    import retest_ea as RT
    ev = []
    for touch, i1, d, Lv, tf_, i0 in RT.setups(dict(RT.BASE, tfs=(tf,), kinds=('wq',))):
        ev.append(dict(t=RT.M15T[touch] + X.L15, side=1 if d == 'up' else -1, tag='w', ref=Lv, win=72))
    return ev
