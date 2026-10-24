"""S: trend pullback (H4MA押し目買い), ported from research/dow_strategy/st_trend.py + st2.py (2026-10-24).

Setup at every H1 close (valid one hour): H4 trend (SMA20 vs SMA75, or H4 provisional Dow) and H1 trend (same choices) agree.
Trigger: M15 provisional Dow turn. Stop: M15 turn protected swing + 0.3 ATR(H1). Exit: H1 swing trail from +act R.
Adopted: XAUUSD S_ma_prov_buy_mt3_h1a1 (half lot), BTCUSD S_ma_ma_buy_mt3_h1a2 (no new entries on Sat/Sun).
"""
import bisect

import numpy as np

from .. import engine as E
from ..core import Frames

STOPS = {'sw3': ('h1swing', 0.3), 'sw8': ('h1swing', 0.8), 'mt3': ('m15turn', 0.3)}
EXITS = {'h1a1': ('h1', 1.0), 'h1a2': ('h1', 2.0), 'h4a1': ('h4', 1.0), 'hyb': ('hyb', 1.0)}
ADOPTED = {'XAUUSD': ('ma', 'prov', 'buy', 'mt3', 'h1a1'), 'BTCUSD': ('ma', 'ma', 'buy', 'mt3', 'h1a2')}
WEEKDAYS_ONLY = {'BTCUSD'}


def events(F: Frames, c4, c1, side):
    h1 = F.h1.reset_index(drop=True); h4 = F.h4.reset_index(drop=True)
    M1 = {n: h1.c.rolling(n).mean().to_numpy() for n in (20, 75)}; M4 = {n: h4.c.rolling(n).mean().to_numpy() for n in (20, 75)}
    P1 = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in F.R1['prov_bars']])
    P4 = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in F.R4['prov_bars']])
    MA1 = np.sign(M1[20] - M1[75]); MA4 = np.sign(M4[20] - M4[75])
    ev = []
    for i, t in enumerate(F.C1):
        k = bisect.bisect_right(F.C4, t) - 1
        if k < 0:
            continue
        a = MA4[k] if c4 == 'ma' else P4[k]; b = MA1[i] if c1 == 'ma' else P1[i]
        if a == 0 or a != b:
            continue
        s = int(a)
        if side.startswith('buy') and s != 1:
            continue
        ev.append(dict(t=t, side=s, tag=f'{c4}{c1}', win=1))
    return ev


def run(F: Frames, c4, c1, side, st, ex, entry_bar=True):
    cfg = dict(trig='dow', stop=STOPS[st][0], buf=STOPS[st][1], exit=EXITS[ex][0], act=EXITS[ex][1], sw=2.0, win=1)
    if side in ('both_d', 'buy_d'):
        cfg['dside'] = 0      # needs the env filter (not used by the adopted versions)
        raise NotImplementedError('dside filter not ported')
    return E.run(F, events(F, c4, c1, side), cfg, entry_bar=entry_bar)
