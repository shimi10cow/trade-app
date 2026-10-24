"""A: return move (リターンムーブ), ported from research/dow_strategy/retest_ea.py config N1 (2026-10-24).

Event on H4: major Dow reversal, provisional turn, or W top/bottom; level = the broken swing (or the W neck).
Retest: within 72 h price comes back to the level (within 0.3 ATR(H4)) from the trade side; cancelled when an M15 bar closes
back through it by more than 0.3 ATR. Trigger: the M15 provisional turn after the touch (up to 24 h after the window).
Filters: H1 close and SMA20 on the trade side of H1 SMA75; with the daily side; |distance from H4 SMA75| <= 3 ATR.
Stop beyond the M15 turn swing + 1.0 ATR(H1), min 10 pips; H1 swing trail from +1R. One position per side. Adopted on EURUSD.
"""
import bisect

import numpy as np
import pandas as pd

from ..core import TF_LEN, Frames
from ..env import Env
from env_recognition.pivots import atr

N1 = dict(tfs=('H4',), kinds=('major', 'prov', 'w'), win=72, tol=0.3, buf=1.0, ma=True, dside=0, maxdev=3)


def events(F: Frames, tf, kinds):
    A4 = atr(F.h4)
    FR = {'H4': (F.h4, F.R4, F.C4, A4), 'H1': (F.h1, F.R1, F.C1, F.A1)}
    df, R, C, A = FR[tf]
    out = []
    if 'major' in kinds:
        out += [(C[e['idx']], e['to'], e['broken_price']) for e in R['events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL']
    if 'prov' in kinds:
        out += [(C[e['idx']], e['to'], e.get('broken_price') or (e.get('h2') if e['to'] == 'up' else e.get('l2')))
                for e in R['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
    if 'w' in kinds:
        out += [(C[e['idx']], 'up' if e['action'] == 'W_BOTTOM' else 'down', e['b']) for e in R['w_events']]
    return [(t, d, L, tf) for t, d, L in out if L is not None], FR


def setups(F: Frames, cfg):
    res = []
    M15T = F.M15T
    for tf in cfg['tfs']:
        evs, FR = events(F, tf, cfg['kinds'])
        df, R, C, A = FR[tf]
        for t, d, L, _ in evs:
            s = 1 if d == 'up' else -1
            k = bisect.bisect_right(C, t) - 1
            band = cfg['tol'] * A[k]
            i0 = M15T.searchsorted(t); i1 = M15T.searchsorted(t + pd.Timedelta(hours=cfg['win']))
            touch = None
            for i in range(i0, min(i1, len(M15T))):
                if s * (F.c[i] - L) < -band:
                    break
                if (F.l[i] <= L + band) if s == 1 else (F.h[i] >= L - band):
                    touch = i
                    break
            if touch is not None:
                res.append((touch, i1, d, L, tf, i0))
    return res


def run(F: Frames, entry_bar=True, env=None, cfg=N1):
    env = env or Env(F.m15_all)
    M15T = F.M15T; n = F.N; L15 = TF_LEN['M15']
    S20 = F.h1.c.rolling(20).mean().to_numpy(); S75 = F.h1.c.rolling(75).mean().to_numpy(); H1C = F.h1.c.to_numpy()
    turn_idx = {}
    for e in F.R15['prov_events']:
        if e['action'] in ('REVERSAL', 'PROV_START'):
            turn_idx.setdefault(e['to'], []).append(e['idx'])
    for d in turn_idx:
        turn_idx[d].sort()
    entries = {}
    for touch, i1, d, L, tf, *_ in setups(F, cfg):
        lst = turn_idx.get(d, [])
        j = bisect.bisect_left(lst, touch)
        if j < len(lst) and lst[j] < i1 + 96:
            entries.setdefault(lst[j], []).append((d, L, tf))
    trades, pos, pending = [], [], []
    h, l, c, o = F.h, F.l, F.c, F.o
    for i in range(n):
        keep = []
        for p in pos:
            if p['k'] > i or (p['k'] == i and not entry_bar):
                keep.append(p); continue
            s = p['side']
            if (l[i] <= p['sl']) if s == 1 else (h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = M15T[i]; p['why'] = 'stop'; trades.append(p); continue
            if not p['trail'] and s * ((h[i] if s == 1 else l[i]) - p['entry']) >= cfg.get('h1act', 1.0) * p['risk']:
                p['trail'] = True
            if p['trail']:
                v = F.last_swing(F.H1P, F.H1PT, M15T[i] + L15, 'lo' if s == 1 else 'hi')
                if v is not None:
                    v -= s * F.PIP
                    if (v < c[i]) if s == 1 else (v > c[i]):
                        p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in entries or M15T[i] < F.START:
            continue
        k1 = bisect.bisect_right(F.C1, M15T[i] + L15) - 1
        for d, L, tf in entries[i]:
            s = 1 if d == 'up' else -1
            if any(p['side'] == s for p in pos):
                continue
            if cfg.get('ma') and not (s * (H1C[k1] - S75[k1]) > 0 and s * (S20[k1] - S75[k1]) > 0):
                continue
            if not env.ok(cfg, M15T[i] + L15, s):
                continue
            swing = F.R15['prov_bars'][i][1]
            if swing is None:
                continue
            if i + 1 >= n:
                pending.append(dict(signal_t=M15T[i], side=s, ref=swing, buf=cfg['buf'] * F.A1[k1], min_risk=10 * F.PIP, tag=tf)); continue
            entry = o[i + 1]; sl = swing - s * cfg['buf'] * F.A1[k1]
            if s * (entry - sl) < 10 * F.PIP:
                sl = entry - s * 10 * F.PIP
            pos.append(dict(k=i + 1, t=M15T[i + 1], side=s, entry=entry, sl=sl, sl0=sl, risk=s * (entry - sl), trail=False, src=tf, tag=tf))
    tr = pd.DataFrame(trades)
    if len(tr):
        tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - F.COST / tr.risk
    return dict(trades=tr, open=pos, pending=pending)
