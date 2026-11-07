"""Q: breakout from a quiet market, ported from research/dow_strategy/q_ea.py (2026-10-24).

Setup at an H1 close: ATR14(H1) below vq x its median of the past 1000 H1 bars, and the close breaks the highest high (buy) /
lowest low (sell) of the previous n H1 bars (one setup per side per range). Direction filter d: 'any' | 'h4' (H4 provisional
trend agrees) | 'ma' (H1 SMA75 rising for buys / falling for sells). Trigger 'now' (next M15 open) or 'dow' (M15 provisional
turn within 12 h). Stop 'ref' = range middle + 0.3 ATR(H1) (or 'h1swing'). Exit: swing trail from +1R on H1 or H4.
Adopted: XAUUSD 0.8/24/ma/now/ref/h1 (half lot), XAGUSD 0.8/24/any/dow/ref/h4, US30 1.0/24/ma/dow/ref/h1.
2026-11-07 (user's chart check of Q@XAUUSD: some entries came after the market had already moved, not out of a quiet range,
because a slow steady trend also has a small ATR): one setting for every market (the gold one) and run_max: skip the setup
when the 24 H1 closes before the breakout bar already moved >= run_max x ATR(H1) the trade way (the setup still counts for the
one-per-range rule, as in the research). On XAUUSD / XAGUSD / BTCUSD (new); Q@US30 is turned off in the app (kept here so the
magic numbers stay the same). 2005-: XAUUSD 724 trades +284R DD 26.5R -> 455 +243R DD 14.3R; XAGUSD 112 +106R -> 351 +122R;
BTCUSD 2017-: 334 trades +278R PF 2.49 DD 13.6R (docs/OPEN_ITEMS.md).
"""
import bisect

import numpy as np
import pandas as pd

from .. import engine as E
from ..core import Frames

ADOPTED = {
    'XAUUSD': (0.8, 24, 'ma', 'now', 'ref', 'h1'),
    'XAGUSD': (0.8, 24, 'ma', 'now', 'ref', 'h1'),      # 2026-11-07: the common setting (was 0.8/24/any/dow/ref/h4 behind the H4 gate)
    'BTCUSD': (0.8, 24, 'ma', 'now', 'ref', 'h1'),      # 2026-11-07: new
    'US30': (1.0, 24, 'ma', 'dow', 'ref', 'h1'),        # off in the app from 2026-11-07
}
OLD_XAGUSD = (0.8, 24, 'any', 'dow', 'ref', 'h4')        # the setting before 2026-11-07 (parity of old results)
RUN_MAX = {'XAUUSD': 3.0, 'XAGUSD': 3.0, 'BTCUSD': 3.0}
E.TRIGGERS.setdefault('now', lambda F: {d: list(range(F.N)) for d in ('up', 'down')})


def events(F: Frames, vq, n, d, run_max=None):
    h1 = F.h1.reset_index(drop=True)
    pc = h1.c.shift(); tr = np.maximum(h1.h - h1.l, np.maximum((h1.h - pc).abs(), (h1.l - pc).abs()))
    ATR = tr.rolling(14).mean(); VR = (ATR / ATR.rolling(1000, min_periods=300).median()).to_numpy()
    M75 = h1.c.rolling(75).mean().to_numpy(); P4 = [b[0] for b in F.R4['prov_bars']]
    C = h1.c.to_numpy()
    HH = h1.h.rolling(n).max().shift(1).to_numpy(); LL = h1.l.rolling(n).min().shift(1).to_numpy()
    ev = []; last = {1: -99, -1: -99}
    for i in range(1100, len(h1)):
        if not (VR[i] < vq):
            continue
        for s, brk in ((1, C[i] > HH[i]), (-1, C[i] < LL[i])):
            if not brk or i - last[s] < n:
                continue
            t = F.C1[i]
            if d == 'h4':
                k4 = bisect.bisect_right(F.C4, t) - 1
                if k4 < 0 or P4[k4] != ('up' if s == 1 else 'down'):
                    continue
            if d == 'ma' and not (np.isfinite(M75[i - 5]) and s * (M75[i] - M75[i - 5]) > 0):
                continue
            last[s] = i
            if run_max is not None and i >= 25 and (C[i - 1] - C[i - 25]) * s / ATR.iloc[i] >= run_max:
                continue                     # no quiet pause before the breakout: the market had already moved
            ev.append(dict(t=t, side=s, tag='q', ref=(HH[i] + LL[i]) / 2, win=12))
    return ev


def run(F: Frames, vq, n, d, trig, stop, ex, entry_bar=True, run_max=None):
    return E.run(F, events(F, vq, n, d, run_max), dict(trig=trig, stop=stop, buf=0.3, exit=ex, act=1.0, win=12), entry_bar=entry_bar)
