"""IX: index H4 turn after a down trend (US30 / US500 / US100 / JP225, buy only), 2026-11-07 (docs/OPEN_ITEMS.md; research scratch
idxdb.py -> idxdb5.py, the user's chart checks). The four indices are treated as one instrument.

Down trend first: the bottom H4 swing low is the 3rd of three falling H4 swing lows (two lower lows) - a correction inside an up
trend (no lower low) does not count. Setups (one per bottom: a double-bottom break and the Dow turn within 6 H4 bars count once):
  T  : the H4 major Dow turns up (an H4 close above the last lower high); bottom = the protected low of the turn
  DB : H4 double bottom - swing lows L1, L2 around the highest swing high Hm between them, L2 within [L1 - 0.3 ATR(H4),
       L1 + half the bounce], L1 itself the 3rd falling low; the first H4 close above Hm (within 60 H4 bars of L2's confirmation,
       before a close below the bottom) while the H4 major trend is still down; bottom = min(L1, L2)
Entry: at the next M15 open after the setup's H4 close. Stop: the bottom - 0.3 ATR(H1). No daily filter.
Exit (whichever first): H1 swing trail from +2R; once +1R, an H4 close below the latest H4 swing low formed after the entry
(engine cfg h4sw); a day closing below the latest confirmed daily swing low above the stop (cfg d1sw).
Research (2017-07 .. 2026-10, the four together, engine run incl. re-entries): 208 trades, win 57%, +0.32R, PF 1.97, +7.1R/yr,
max DD 8.5R, worst year -4.1R, both halves +, top 5% excluded +0.21R. Not included: swap (held 13 days median) - check later.
"""
import bisect

import numpy as np
import pandas as pd

from .. import engine as E
from ..core import Frames
from env_recognition.pivots import atr

E.TRIGGERS.setdefault('now', lambda F: {d: list(range(F.N)) for d in ('up', 'down')})
CFG = dict(trig='now', stop='ref', buf=0.3, exit='h1', act=2.0, sw=2.0, h4sw=1.0, d1sw=True)
DEDUPE = 6          # H4 bars: a setup this close to the previous one (same bottom) is skipped


def setups(F: Frames):
    """[(kind, H4 bar index of the setup close, bottom price)] for setups after a down trend, in time order, one per bottom."""
    h4 = F.h4.reset_index(drop=True); H4c = h4.c.to_numpy(float); A4 = np.asarray(atr(h4), float); n4 = len(h4)
    r4 = [b[0] for b in F.R4['bars']]
    PV = sorted(F.R4['pivot_events'], key=lambda e: e['idx'])
    LO = [e for e in PV if e['kind'] == 'lo']; HI = [e for e in PV if e['kind'] == 'hi']; LOI = [e['idx'] for e in LO]

    def falling_into(e):
        j = LOI.index(e['idx'])
        return j >= 2 and LO[j - 2]['price'] > LO[j - 1]['price'] > LO[j]['price']

    out = []
    for e in F.R4['events']:
        if e.get('machine') == 'major' and e['action'] == 'REVERSAL' and e.get('to') == 'up':
            k = e['idx']; p = F.R4['bars'][k][1]
            cand = [x for x in LO if x['idx'] <= k and x['available_idx'] <= k and abs(x['price'] - p) < 1e-9]
            if cand and falling_into(cand[-1]):
                out.append(('T', k, p))
    for j in range(1, len(LO)):
        L1, L2 = LO[j - 1], LO[j]
        mids = [x for x in HI if L1['idx'] < x['idx'] < L2['idx']]
        if not mids:
            continue
        Hm = max(mids, key=lambda x: x['price']); a = A4[L2['idx']]
        if not np.isfinite(a) or not (L1['price'] - 0.3 * a <= L2['price'] <= L1['price'] + 0.5 * (Hm['price'] - L1['price'])):
            continue
        if not falling_into(L1):
            continue
        bot = min(L1['price'], L2['price'])
        for x in range(L2['available_idx'], min(n4, L2['available_idx'] + 60)):
            if H4c[x] < bot:
                break
            if H4c[x] > Hm['price']:
                if r4[x] == 'down':
                    out.append(('DB', x, bot))
                break
    out.sort(key=lambda s: s[1])
    kept, last = [], -10
    for kind, k, bot in out:
        if k - last >= DEDUPE:
            kept.append((kind, k, bot))
        last = k
    return kept


def events(F: Frames):
    C4 = pd.DatetimeIndex(F.C4); CL = pd.DatetimeIndex(F.CL15); ev = []
    for kind, k, bot in setups(F):
        i = int(CL.searchsorted(C4[k], side='left'))          # the M15 bar closing with the setup's H4 bar
        if i >= F.N:
            continue                                        # the H4 bar is not closed yet
        ev.append(dict(t=CL[i], side=1, win=0.1, tag=f'{kind}', ref=bot))
    return ev


def run(F: Frames, entry_bar=True):
    return E.run(F, events(F), CFG, entry_bar=entry_bar)
