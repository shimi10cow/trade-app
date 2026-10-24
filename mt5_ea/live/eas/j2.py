"""J2: H1 Dow turn follower (H1 ダウ転換), ported from research/dow_strategy/turn_ea.py + turn_tune.py + turn_tune2.py (2026-10-24).

Setup: an M15 provisional turn made BEFORE the M15 major trend turned, with the H4 provisional trend the same way, the H1 major
trend the same way, and the M15 bar starting between 00:00 and 10:00 broker time. Entry at the next M15 open.
Stop beyond the provisional protected swing + 0.3 ATR(H1). Exit: H1 swing trail from +1R. Adopted on USDJPY (jt2_h1major+hour0_10).
"""
import bisect

import numpy as np
import pandas as pd

from .. import engine as E
from ..core import Frames

E.TRIGGERS.setdefault('now', lambda F: {d: list(range(F.N)) for d in ('up', 'down')})
CFG = dict(trig='now', stop='ref', buf=0.3, exit='h1', act=1.0, win=1)
ADOPTED = {'USDJPY': dict(h1='h1major', hours=(0, 10))}


def events(F: Frames, h1mode='h1major', hours=(0, 10)):
    R, CL = F.R15, list(F.CL15)
    ev = []
    for e in R['prov_events']:
        if e['action'] not in ('REVERSAL', 'PROV_START'):
            continue
        i = e['idx']; to = e['to']; s = 1 if to == 'up' else -1
        if R['bars'][i][0] == to:
            continue
        ref = R['prov_bars'][i][1]
        if ref is None or not np.isfinite(ref):
            continue
        t = CL[i]
        k4 = bisect.bisect_right(F.C4, t) - 1
        if k4 < 0 or F.R4['prov_bars'][k4][0] != to:
            continue
        ev.append(dict(t=t, side=s, tag='turnM15', ref=ref, win=1))
    out = []
    for e in ev:                                    # turn_tune.h1filter, applied in the order of turn_tune2.ev_for
        k1 = bisect.bisect_right(F.C1, e['t']) - 1; d = 'up' if e['side'] == 1 else 'down'
        if h1mode == 'h1major' and F.R1['bars'][k1][0] != d:
            continue
        out.append(e)
    if hours:
        out = [e for e in out if hours[0] <= (e['t'] - pd.Timedelta(minutes=15)).hour < hours[1]]
    return out


def run(F: Frames, h1='h1major', hours=(0, 10), entry_bar=True):
    return E.run(F, events(F, h1, hours), CFG, entry_bar=entry_bar)
