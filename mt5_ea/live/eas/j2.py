"""J2: H1 Dow turn follower (H1 ダウ転換), ported from research/dow_strategy/turn_ea.py + turn_tune.py + turn_tune2.py (2026-10-24).

Setup: an M15 provisional turn made BEFORE the M15 major trend turned, with the H4 provisional trend the same way, the H1 major
trend the same way, and the M15 bar starting between 00:00 and 10:00 broker time. Entry at the next M15 open.
Stop beyond the provisional protected swing + 0.3 ATR(H1). Exit: H1 swing trail from +1R. Adopted on USDJPY (jt2_h1major+hour0_10).
2026-11-04 (RESEARCH_LOG §170 / §174): no hour window; instead only when the WEEKLY major Dow trend is the trade's way (J2 rides the
continuation of the H1 / H4 move; against the weekly trend that move is a correction: those trades were -0.04R in both halves).
The weekly trend needs ~8 years of weekly bars, so it comes from the broker's W1 bars (F.W1, set by the runner), not from M15.
2026-11-08 (user's J2 trade check: "decide M15 or H1 exit by the trend stage"): when the H4 major Dow trend is the trade's way and
already at its 4th leg or later (turn = 1st leg, +1 per breakout), the trail follows M15 swings instead of H1 (late H4 trend: the H1
turn is often its last push). Broker-time data 2005-: 227 -> 231 trades, total +113 -> +120R, max DD 16.0 -> 14.0R, better in 3 of 4
quarters. Daily-Dow stages did worse (J2's best trades are in the daily trend's 2nd-3rd leg). Entries before CUTOVER keep the H1 trail.
"""
import bisect

import numpy as np
import pandas as pd

from .. import engine as E
from ..core import Frames
from .h4gate import _when
from env_recognition import dow_trend

E.TRIGGERS.setdefault('now', lambda F: {d: list(range(F.N)) for d in ('up', 'down')})
CFG = dict(trig='now', stop='ref', buf=0.3, exit='h1', act=1.0, win=1)
ADOPTED = {'USDJPY': dict(h1='h1major', hours=None, weekly=True, late_legs=4, lhx=True)}
LH_CUTOVER = pd.Timestamp('2026-11-08 00:00')   # the lower-high exit (2026-11-07) applies to setups from here in live
CUTOVER = pd.Timestamp('2026-11-08 00:00')   # the H4-stage exit applies to entries from here on


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


def weekly_trend(w1):
    """Weekly major Dow trend known at each time: function t -> +1 / -1 / 0 (last weekly bar CLOSED by t; bar t = its open)."""
    df = w1[['t', 'o', 'h', 'l', 'c']].reset_index(drop=True)
    R = dow_trend.run(df, 'W1')
    end = (pd.to_datetime(df.t) + pd.Timedelta(days=7)).to_numpy()
    tr = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['bars']])

    def at(t):
        k = int(np.searchsorted(end, np.datetime64(pd.Timestamp(t)), side='right')) - 1
        return int(tr[k]) if k >= 0 else 0
    return at


def h4_legs(F: Frames):
    """(t, side) -> leg of the H4 major Dow trend known at t when it points the side's way (1 = just turned, +1 per breakout),
    0 when it points the other way."""
    R = F.R4; n = len(R['bars']); trend = [b[0] for b in R['bars']]; legs = np.zeros(n, int); evs = {}
    for e in R['events']:
        if e.get('machine') == 'major' and e['action'] in ('BREAKOUT', 'REVERSAL'):
            evs.setdefault(e['idx'], []).append(e['action'])
    cnt = 0
    for k in range(n):
        for a in evs.get(k, []):
            cnt = 1 if a == 'REVERSAL' else cnt + 1
        if k > 0 and trend[k] != trend[k - 1] and 'REVERSAL' not in evs.get(k, []):
            cnt = 1
        legs[k] = cnt

    def at(t, s):
        k = bisect.bisect_right(F.C4, t) - 1
        return int(legs[k]) if k >= 0 and trend[k] == ('up' if s == 1 else 'down') else 0
    return at


def run(F: Frames, h1='h1major', hours=None, weekly=False, entry_bar=True, late_legs=None, cutover=None, lhx=False, lh_cutover=None):
    """late_legs: M15 trail for setups made when the H4 trend is at that leg or later; only from `cutover` (default CUTOVER,
    False = the whole history, for research / parity).
    lhx (2026-11-07, docs/OPEN_ITEMS.md): once +1R, close at the first confirmed H1 swing high lower than the previous one after
    the entry (sells: higher low) - USDJPY turns by lower highs; only for setups from `lh_cutover` (default LH_CUTOVER, False = all).
    2006-: 231 trades +119.8R DD 14.0R -> +133.5R DD 12.5R (both halves better, the 10 largest wins unchanged)."""
    ev = events(F, h1, hours)
    if late_legs:
        legs = h4_legs(F); cut = CUTOVER if cutover is None else cutover
        ev = [dict(e, xk='m15') if (cut is False or e['t'] >= cut) and legs(e['t'], e['side']) >= late_legs else e for e in ev]
    if lhx:
        lc = LH_CUTOVER if lh_cutover is None else lh_cutover
        ev = [dict(e, lhx=True) if (lc is False or e['t'] >= lc) else e for e in ev]
    r = E.run(F, ev, CFG, entry_bar=entry_bar)
    if not weekly:
        return r
    w1 = getattr(F, 'W1', None)
    if w1 is None or len(w1) < 430:          # too few weekly bars (the trend needs ~8 years): manage what is open, no new entries
        return dict(r, pending=[])
    wt = weekly_trend(w1); ok = lambda t, s: wt(t) == int(s)
    tr = r['trades']
    if isinstance(tr, pd.DataFrame) and len(tr):
        tr = tr[[ok(t, s) for t, s in zip(tr.t, tr.side)]].reset_index(drop=True)
    return dict(r, trades=tr, open=[p for p in r['open'] if ok(_when(p), p['side'])], pending=[p for p in r['pending'] if ok(_when(p), p['side'])])
