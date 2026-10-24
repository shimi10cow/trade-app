"""C: M15 correction line break (M15調整TL抜け), ported from research/dow_strategy/m15_corr_lines.py + step2_newea.cl15_events +
step2b_cl15.py (md4tri) + cl15_feat.py (USDJPY line-strength filter) (2026-10-24).

Line: a correction of the preceding M15 impulse (A tops a move of >= 6 ATR(M15) over 96 bars, A = highest high of the previous
40 bars), B = a later lower swing high (>= 0.6 ATR lower, clear trough >= 1.5 ATR, within 40 bars); the line through A and B,
re-drawn as the outer tangent over later lower highs. Break = close beyond the line -> buy (mirror for sell).
Entry: M15 provisional turn within 4 h; stop beyond the M15 turn swing + 1.0 ATR(H1); H1 swing trail from +1R.
Environment (md4tri): with the daily side (sd > 0), |distance from H4 SMA75| <= 4 ATR, no H4 triangle forming.
USDJPY only: lines with the correction lasting > 24 M15 bars and slope > 0.03 ATR(M15) per bar.
Note: like the research, the line start A uses the final known version of the pivot (pivots can relocate later); the cut test
(parity test 2) shows whether that changes live trades.
"""
import bisect

import numpy as np

from .. import engine as E
from ..core import Frames
from ..env import Env
from env_recognition.pivots import atr

LOOK, DROP, PROM, MAXAB, MAXLEN, IMPW, IMP = 40, 0.6, 1.5, 40, 300, 96, 6.0
CFG = dict(trig='dow', stop='m15turn', buf=1.0, exit='h1', act=1.0, dside=0, maxdev=4, notri='H4')
# USDJPY: the research workspace had no triangle file (results/tri_intervals.csv missing), so its validated C ran WITHOUT the
# H4-triangle filter; the live USDJPY C does the same (parity test 1: 5 trades differed with the filter on).
ADOPTED = {'EURUSD': dict(strength=False, notri=True), 'USDJPY': dict(strength=True, notri=False)}


def lines(F: Frames):
    H, L, C = F.h, F.l, F.c; A15 = atr(F.m15); n = len(F.T15)
    last = {}
    for e in F.R15['pivot_events']:
        last[e['id']] = e
    piv = sorted((e['idx'], e['kind'], e['price'], e['available_idx']) for e in last.values())
    byk = {k: [p for p in piv if p[1] == k] for k in ('hi', 'lo')}
    byk_i = {k: [p[0] for p in v] for k, v in byk.items()}
    out = []
    for ia, kind, pa, avail in piv:
        hi = kind == 'hi'; s = -1 if hi else 1
        j0 = max(0, ia - LOOK)
        if (hi and H[j0:ia].size and H[j0:ia].max() > pa) or ((not hi) and L[j0:ia].size and L[j0:ia].min() < pa):
            continue
        a = A15[ia]
        if not np.isfinite(a) or a <= 0 or ia < IMPW:
            continue
        origin = L[ia - IMPW:ia + 1].min() if hi else H[ia - IMPW:ia + 1].max()
        if (pa - origin if hi else origin - pa) < IMP * a:
            continue
        lo_, hi_ = bisect.bisect_right(byk_i[kind], ia), bisect.bisect_right(byk_i[kind], ia + MAXLEN)
        later = sorted(byk[kind][lo_:hi_], key=lambda p: p[3])
        b = slope = created = None; q = 0; end = None; broken = False
        for j in range(ia + 1, min(n, ia + MAXLEN)):
            while q < len(later) and later[q][3] <= j:
                pb = later[q]; q += 1
                if b is None:
                    if pb[0] - ia > MAXAB:
                        continue
                    if s * (pb[2] - pa) < DROP * a:
                        continue
                    seg = L[ia:pb[0] + 1] if hi else H[ia:pb[0] + 1]
                    trough = seg.min() if hi else seg.max()
                    if (pb[2] - trough if hi else trough - pb[2]) < PROM * a:
                        continue
                    b, slope, created = pb, (pb[2] - pa) / (pb[0] - ia), j
                else:
                    sl = (pb[2] - pa) / (pb[0] - ia)
                    if (sl > slope) if hi else (sl < slope):
                        slope, b = sl, pb
            if (H[j] > pa) if hi else (L[j] < pa):
                end = j; break
            if (C[j] < origin) if hi else (C[j] > origin):
                end = j; break
            if slope is not None:
                v = pa + slope * (j - ia)
                if (C[j] > v) if hi else (C[j] < v):
                    end, broken = j, True; break
        if b is None:
            continue
        out.append((ia, pa, b[0], b[2], created, end, kind, broken))
    return out, A15


def events(F: Frames):
    """Setups with the line strength in the tag: dur (bars from A to the break) | slope (|slope| per bar in ATR(M15))."""
    ev = []
    LS, A15 = lines(F)
    for ia, pa, ib, pb, cr, en, kind, broken in LS:
        if not broken or en is None:
            continue
        s = 1 if kind == 'hi' else -1
        seg = F.l[ia:en + 1] if s == 1 else F.h[ia:en + 1]
        ref = seg.min() if s == 1 else seg.max()
        a = A15[en] if np.isfinite(A15[en]) and A15[en] > 0 else A15[ia]
        ev.append(dict(t=F.CL15[en], side=s, tag=f'{en - ia}|{abs((pb - pa) / (ib - ia)) / a:.4f}', ref=ref, win=4))
    return ev


def strong(tag):
    dur, slope = tag.split('|')
    return int(dur) > 24 and float(slope) > 0.03


def run(F: Frames, strength=False, entry_bar=True, env=None, notri=True):
    """strength (USDJPY): run with every line (as the research did), then keep only trades from strong lines."""
    env = env or Env(F.m15_all)
    cfg = CFG if notri else {k: v for k, v in CFG.items() if k != 'notri'}
    r = E.run(F, events(F), cfg, env_ok=env.ok, entry_bar=entry_bar)
    if not strength:
        return r
    tr = r['trades']
    if len(tr):
        tr = tr[[strong(t) for t in tr.tag]].reset_index(drop=True)
    return dict(trades=tr, open=[p for p in r['open'] if strong(p['tag'])], pending=[p for p in r['pending'] if strong(p['tag'])])
