"""Trendline EAs (2026-11-07, docs/OPEN_ITEMS.md; research scratch zone.py stage J / h4zone.py + h4rule.py).

Lines (tlines.build, the user's rules): points are confirmed Dow swings; the 1st point is the top since the last reset, a point
counts once a pullback swing is confirmed (provisional line), the line is confirmed when the low (high) updates beyond the pullback;
a next point within 0.5 ATR of the line refits it, a clearly steeper one redraws it from the previous point; a close beyond the line
deletes it, and a major Dow turn against it deletes it too.

DL (daily line, EURUSD / USDJPY): daily lines (lines older than 60 days at the 1st point are redrawn, a close beyond = a daily close).
  Zone: H1 bars whose near side is within 0.5 ATR(D1) of a live line (a 0.3 ATR pierce allowed), one entry per visit.
  Trigger: M15 provisional Dow turn while the last closed H1 close is beyond H1 SMA20 and SMA20 rises (falls) over 3 bars.
  Stop: the farther of the M15 turn swing and the line, + 0.5 ATR(H1). Exit: M15 swing trail from +1R.
HL (H4 line, EURUSD): H4 lines (a close beyond = an H4 close; the H4 major Dow turning deletes the line).
  Zone: H1 bars within 1.0 ATR(H4) of a live line whose slope is at most 1 ATR(H4) per day (6 H4 bars), one entry per visit.
  Trigger: the first M15 correction-line break (C's lines) in the visit, skipped when H1 SMA20/75 are in the trade's order but SMA75
  does not slope the trade way over 10 bars; the visit is dropped when, at that trigger, the line is already confirmed (the trend
  ran and came back) or the H4 major Dow points against the trade.
  Stop: the farther of the M15 turn swing and the line, + 0.5 ATR(H1). Exit: H1 swing trail from +1R.

Live note: a line is alive until the bar whose close breaks it (the research stopped the zone one bar earlier, on the breaking
day / H4 bar itself); the daily lines use complete days only.
"""
import bisect

import numpy as np
import pandas as pd

from .. import engine as E
from ..core import Frames
from . import c as C_
from . import tlines
from env_recognition import dow_trend
from env_recognition.pivots import atr

lval = lambda ln, x: ln['anchor'][1] + ln['slope'] * (x - ln['anchor'][0])


def _daily(F: Frames, research=False):
    m = F.m15_all.set_index('t')
    D = m.resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    last = pd.Timestamp(F.m15_all.t.iat[-1])
    if not research and (last.hour != 23 or last.minute != 45):          # the current day is not complete yet
        D = D[pd.to_datetime(D.t) < last.normalize()].reset_index(drop=True)
    return D


def _visits(lines, zone, T_hi, frac, A, H1h, H1l, C1, gap=6, angle_max=None, A_ang=None, research=False):
    """zone visits on H1 bars: (start, end, side, line). T_hi: the line's bar index (day / H4) of each H1 bar."""
    out = []; n1 = len(H1h)
    for ln in lines:
        s = -1 if ln['side'] == -1 else 1
        if angle_max is not None and abs(ln['slope']) / A_ang[ln['anchor'][0]] * 6 > angle_max:
            continue
        j0 = int(np.searchsorted(T_hi, ln['valid'] + 1, side='left'))
        if research:                                    # parity with the research: the zone ends one bar before the line's end
            j1 = int(np.searchsorted(T_hi, ln['end'], side='left'))
        else:
            j1 = n1 if ln['why'] == 'open' else int(np.searchsorted(T_hi, ln['end'], side='right'))
        cur = None; out_n = 0
        for j in range(j0, j1):
            k = T_hi[j]; a = A[k]
            if not np.isfinite(a) or a <= 0:
                continue
            v = lval(ln, k + frac[j]); dist = (v - H1h[j]) / a if s == -1 else (H1l[j] - v) / a
            if -0.3 <= dist <= zone:
                if cur is None:
                    cur = [C1[j], C1[j], s, ln]
                cur[1] = C1[j]; out_n = 0
            elif cur is not None:
                out_n += 1
                if out_n > gap:
                    out.append(tuple(cur)); cur = None
        if cur is not None:
            out.append(tuple(cur))
    return out


def _trig_dowma(F):
    h1c = F.h1.c.to_numpy(float); S20 = F.H1MA[20]; C1 = list(F.C1)
    base = E._trigger(F, 'dow'); out = {}
    for d, lst in base.items():
        s = 1 if d == 'up' else -1; keep = []
        for i in lst:
            k = bisect.bisect_right(C1, F.CL15[i]) - 1
            if k >= 3 and (h1c[k] - S20[k]) * s > 0 and (S20[k] - S20[k - 3]) * s > 0:
                keep.append(i)
        out[d] = keep
    return out


def _trig_m15tlx(F):
    S20, S75 = F.H1MA[20], F.H1MA[75]; C1 = list(F.C1); out = {'up': [], 'down': []}
    for ia, pa, ib, pb, cr, en, kind, broken in C_.lines(F)[0]:
        if not (broken and en is not None):
            continue
        s = 1 if kind == 'hi' else -1; k = bisect.bisect_right(C1, F.CL15[en]) - 1
        if (S20[k] - S75[k]) * s > 0 and (S75[k] - S75[k - 10]) * s <= 0:
            continue                                    # H1 MA order with the trade but SMA75 not sloping with it
        out['up' if s == 1 else 'down'].append(en)
    return {k: sorted(v) for k, v in out.items()}


E.TRIGGERS.setdefault('tl_dowma', _trig_dowma)
E.TRIGGERS.setdefault('tl_m15tlx', _trig_m15tlx)


def daily_lines(F: Frames, research=False):
    D = _daily(F, research); RD = dow_trend.run(D[['t', 'o', 'h', 'l', 'c']], 'D1'); AD = np.asarray(atr(D), float)
    return D, AD, tlines.build(D, RD, AD, 'D1', early=True, h4c=None, maxspan=60)


def run_daily(F: Frames, zone=0.5, research=False):
    """DL: returns dict(trades, open, pending). research=True: the research's zone end (parity only)."""
    D, AD, lines = daily_lines(F, research); TD = pd.DatetimeIndex(pd.to_datetime(D.t))
    h1 = F.h1.reset_index(drop=True); T1 = pd.to_datetime(h1.t)
    dayix = TD.searchsorted(T1, side='right') - 1
    frac = ((T1 - TD[np.clip(dayix, 0, None)].values) / pd.Timedelta('1D')).to_numpy()
    keep = dayix >= 0
    V = _visits(lines, zone, np.where(keep, dayix, 0), frac, AD, h1.h.to_numpy(float), h1.l.to_numpy(float), pd.DatetimeIndex(F.C1),
                research=research)

    def line_at(ln):
        def f(ts):
            d = int(TD.searchsorted(ts, side='right') - 1); return lval(ln, d + (ts - TD[d]) / pd.Timedelta('1D'))
        return f
    ev = [dict(t=a, side=int(s), win=max(1.0, (b - a) / pd.Timedelta('1h') + 1), tag='dl', line_at=line_at(ln)) for a, b, s, ln in V]
    return E.run(F, ev, dict(trig='tl_dowma', stop='far', buf=0.5, exit='m15', act=1.0, one_per_side=True))


def run_h4(F: Frames, zone=1.0, angle_max=1.0, research=False):
    """HL: returns dict(trades, open, pending). research=True: the research's zone end (parity only)."""
    h4 = F.h4.reset_index(drop=True); A4 = np.asarray(atr(h4), float); T4 = pd.DatetimeIndex(pd.to_datetime(h4.t))
    lines = tlines.build(h4, F.R4, A4, 'H4', early=True, h4c=None)
    h1 = F.h1.reset_index(drop=True); T1 = pd.to_datetime(h1.t)
    k4of = T4.searchsorted(T1, side='right') - 1
    frac = ((T1 - T4[np.clip(k4of, 0, None)].values) / pd.Timedelta('4h')).to_numpy()
    V = _visits(lines, zone, np.clip(k4of, 0, None), frac, A4, h1.h.to_numpy(float), h1.l.to_numpy(float), pd.DatetimeIndex(F.C1),
                angle_max=angle_max, A_ang=A4, research=research)
    tr4 = [b[0] for b in F.R4['bars']]; CL15 = pd.DatetimeIndex(F.CL15)

    def line_at(ln):
        def f(ts):
            k = int(T4.searchsorted(ts, side='right') - 1); return lval(ln, k + (ts - T4[k]) / pd.Timedelta('4h'))
        return f

    def ok(ln, s):
        def f(i):
            k = int(T4.searchsorted(CL15[i], side='right')) - 2          # the last closed H4 bar at the trigger
            cf = ln.get('conf')
            if cf is not None and cf <= k:
                return False                                            # the line is confirmed: the trend already ran
            return tr4[k] == ('up' if s == 1 else 'down')               # the H4 major Dow points the trade's way
        return f
    ev = [dict(t=a, side=int(s), win=max(1.0, (b - a) / pd.Timedelta('1h') + 1), tag=str(a), line_at=line_at(ln), ok=ok(ln, int(s)))
          for a, b, s, ln in V]
    return E.run(F, ev, dict(trig='tl_m15tlx', stop='far', buf=0.5, exit='h1', act=1.0, one_per_side=True))
