"""RM: return move after a long H4 trend (新リターンムーブ), research trendlab/rm/run8.py (RESEARCH_LOG §164-§166, 2026-11-03).

Setup on H4:
  1 an H4 provisional Dow turn (REVERSAL / PROV_START) with a broken price L; s = the new trend's side
  2 the trend it ended was long: >= 50 H4 bars since the previous provisional turn the other way
  3 a breakout bar: an M15 close beyond L inside the H4 turn bar (the 4 h before its close)
  4 after the H4 bar closed, price leaves L by >= 1 ATR(H4) (the peak) and comes back to L +/- 0.3 ATR(H4) at least 6 h after
    the turn and within 10 days (the touch); before the touch no M15 close beyond L against the trade by > 0.2 ATR(H4)
Trigger: the first M15 provisional Dow turn to s after the touch, within 48 h; cancelled when an M15 close goes beyond L against
the trade by > 0.5 ATR(H4) or runs > 2.5 ATR(H4) the trade way first. Entry at the next M15 open.
Stop: the lowest low (highest high for sells) from the touch to the trigger bar -/+ 0.2 ATR(H1).
Exit: once +2R was reached, the stop follows the last confirmed M15 swing (no buffer) that is below (above) the close; at most
20 days. One position per side. Adopted on EURUSD and XAUUSD (the A@EURUSD return move stays off).
"""
import bisect

import numpy as np
import pandas as pd

from ..core import TF_LEN, Frames
from env_recognition.pivots import atr

CFG = dict(pre=50, peak=1.0, near=0.3, min_h=6, days=10, tol_pre=0.2, tol=0.5, run=2.5, win_h=48, buf=0.2, act=2.0, max_days=20)
ADOPTED = ('EURUSD', 'XAUUSD')


def setups(F: Frames, cfg=CFG):
    """(trigger bar i, side, stop ref = lowest low since the touch, ATR(H1) at i, tag) for every setup, in data order."""
    T = F.M15T.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = F.N
    C4 = list(F.C4); A4 = atr(F.h4); C1 = np.array(F.C1, dtype='datetime64[ns]'); CL = T + np.timedelta64(15, 'm')
    turn = {d: np.array(sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d))
            for d in ('up', 'down')}
    prv = sorted([e for e in F.R4['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')], key=lambda e: e['idx'])
    out = []
    for k, e in enumerate(prv):
        L = e.get('broken_price')
        if L is None:
            continue
        prev = next((prv[j]['idx'] for j in range(k - 1, -1, -1) if prv[j]['to'] != e['to']), None)
        if prev is None or e['idx'] - prev < cfg['pre']:
            continue
        s = 1 if e['to'] == 'up' else -1
        t4 = C4[e['idx']]; a4 = A4[bisect.bisect_right(C4, t4) - 1]
        if not np.isfinite(a4) or a4 <= 0:
            continue
        i0 = int(np.searchsorted(T, np.datetime64(t4)))
        if i0 >= n:
            continue
        ib0 = int(np.searchsorted(T, np.datetime64(t4) - np.timedelta64(4, 'h')))
        if not any((c[i] - L) * s > 0 for i in range(ib0, i0)):
            continue
        peak, peak_i, touch = 0.0, None, None
        for i in range(i0, min(i0 + 96 * cfg['days'], n)):
            if s * (c[i] - L) < -cfg['tol_pre'] * a4:
                break
            x = ((h[i] - L) if s == 1 else (L - l[i])) / a4
            if x > peak:
                peak, peak_i = x, i
            if peak >= cfg['peak'] and i > peak_i and ((l[i] <= L + cfg['near'] * a4) if s == 1 else (h[i] >= L - cfg['near'] * a4)) \
                    and (i - i0) >= cfg['min_h'] * 4:
                touch = i
                break
        if touch is None:
            continue
        lst = turn[e['to']]; q = int(np.searchsorted(lst, touch))
        for i in range(touch, min(touch + cfg['win_h'] * 4, n)):
            if -s * (c[i] - L) > cfg['tol'] * a4 or s * (c[i] - L) > cfg['run'] * a4:
                break
            if q < len(lst) and lst[q] <= i:
                ref = l[touch:i + 1].min() if s == 1 else h[touch:i + 1].max()
                k1 = max(int(np.searchsorted(C1, CL[i], side='right')) - 1, 0)
                out.append((i, s, float(ref), float(F.A1[k1]), 'PRV'))
                break
    return out


def run(F: Frames, entry_bar=True, cfg=CFG):
    M15T = F.M15T; n = F.N; L15 = TF_LEN['M15']
    entries = {}
    for i, s, ref, a1, tag in setups(F, cfg):
        entries.setdefault(i, []).append((s, ref, a1, tag))
    trades, pos, pending = [], [], []
    h, l, c, o = F.h, F.l, F.c, F.o
    max_bars = 96 * cfg['max_days']
    for i in range(n):
        keep = []
        for p in pos:
            if p['k'] > i or (p['k'] == i and not entry_bar):
                keep.append(p); continue
            s = p['side']
            if (l[i] <= p['sl']) if s == 1 else (h[i] >= p['sl']):
                p['exit'] = min(p['sl'], o[i]) if s == 1 else max(p['sl'], o[i])
                p['exit_t'] = M15T[i]; p['why'] = 'stop'; trades.append(p); continue
            if not p['trail'] and s * ((h[i] if s == 1 else l[i]) - p['entry']) >= cfg['act'] * p['risk']:
                p['trail'] = True
            if p['trail']:
                v = F.last_swing(F.P15, F.P15T, M15T[i] + L15, 'lo' if s == 1 else 'hi')
                if v is not None and (v - p['sl']) * s > 0 and (v - c[i]) * s < 0:
                    p['sl'] = v
            if i - p['k'] >= max_bars - 1:
                p['exit'] = c[i]; p['exit_t'] = M15T[i]; p['why'] = 'time'; trades.append(p); continue
            keep.append(p)
        pos = keep
        if i not in entries or M15T[i] < F.START:
            continue
        for s, ref, a1, tag in entries[i]:
            if any(p['side'] == s for p in pos):
                continue
            if i + 1 >= n:
                pending.append(dict(signal_t=M15T[i], side=s, ref=ref, buf=cfg['buf'] * a1, min_risk=0.0, tag=tag)); continue
            entry = o[i + 1]; sl = ref - s * cfg['buf'] * a1
            if s * (entry - sl) <= 0:
                continue
            pos.append(dict(k=i + 1, t=M15T[i + 1], side=s, entry=entry, sl=sl, sl0=sl, risk=s * (entry - sl), trail=False, tag=tag))
    tr = pd.DataFrame(trades)
    if len(tr):
        tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - F.COST / tr.risk
    return dict(trades=tr, open=pos, pending=pending)
