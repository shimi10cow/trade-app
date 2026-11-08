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
2026-11-08 FX Q (run_fx, AUDJPY; docs/OPEN_ITEMS.md D13): the same setups (gold setting + run_max 3) with the H4 major Dow trend the
trade's way (any leg; on the yen pairs Q only works with the H4 trend) and the daily side (H4 close beyond H4 SMA1200); stop the range
middle + 0.3 ATR(H1); exit: until +1.5R only an H4 close below the latest H4 swing low formed after the entry (engine h4sw=0), from
+1.5R the H1 swing trail (AUDJPY pulls back deep: an H1 trail from +1R leaves too early; an M15 trail cut the moves in half).
Research data -> server time, 2005-2026: AUDJPY 159 trades +0.53R PF 1.90 max DD 9.2R, both halves +0.52 / +0.54. USDJPY with the same
rule: 181 trades +0.36R, but it moves with the USDJPY EAs and loses in the portfolio's bad months -> not used. EURUSD: the H4 / daily
trend does not help Q (a pullback market) -> not used. With the 28 app EAs (2017-07..): 1% risk 249% -> 260% a year, DD 19.0 -> 19.6%.
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
# 2026-11-07 (docs/OPEN_ITEMS.md, silver Q loss review): silver only, skip a breakout whose stop would be far - the range did not
# really contract: s * (breakout close - range middle) / ATR14(H1) + 0.3 >= FAR_MAX (= the stop distance in ATR(H1)). Silver
# reverts (variance ratio 0.990 vs gold 1.012), so a break out of a wide range is often a fake; on gold / BTC the wide ones still
# pay (+0.25 / +0.63R) and stay. 2005-: 351 trades +122R DD 15.1R -> 254 +140R DD 7.3R, PF 1.61 -> 2.04. Setups from FAR_FROM.
FAR_MAX = {'XAGUSD': 3.5}
FAR_FROM = {'XAGUSD': pd.Timestamp('2026-11-09 00:00')}
E.TRIGGERS.setdefault('now', lambda F: {d: list(range(F.N)) for d in ('up', 'down')})


def events(F: Frames, vq, n, d, run_max=None, far_max=None, far_from=None):
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
            if far_max is not None and (far_from is None or t >= far_from) and s * (C[i] - (HH[i] + LL[i]) / 2) / ATR.iloc[i] + 0.3 >= far_max:
                continue                     # the range did not contract: the stop (range middle) would be far
            ev.append(dict(t=t, side=s, tag='q', ref=(HH[i] + LL[i]) / 2, win=12))
    return ev


def run(F: Frames, vq, n, d, trig, stop, ex, entry_bar=True, run_max=None, far_max=None, far_from=None):
    return E.run(F, events(F, vq, n, d, run_max, far_max, far_from), dict(trig=trig, stop=stop, buf=0.3, exit=ex, act=1.0, win=12), entry_bar=entry_bar)


FX_CFG = dict(trig='now', stop='ref', buf=0.3, win=12, exit='h1', act=1.5, h4sw=0.0, dside=0)


def run_fx(F: Frames, env=None, entry_bar=True):
    """FX Q (AUDJPY): gold-setting setups with the H4 major Dow trend the trade's way, the daily side; see the module note."""
    from ..env import Env
    from .j2 import h4_legs
    env = env or Env(F.m15_all); legs = h4_legs(F)
    ev = [e for e in events(F, 0.8, 24, 'ma', run_max=3.0) if legs(e['t'], e['side']) >= 1]
    return E.run(F, ev, FX_CFG, env_ok=env.ok, entry_bar=entry_bar)
