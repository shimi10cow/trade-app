"""S: trend pullback (H4MA押し目買い), ported from research/dow_strategy/st_trend.py + st2.py (2026-10-24).

Setup at every H1 close (valid one hour): H4 trend (SMA20 vs SMA75, or H4 provisional Dow) and H1 trend (same choices) agree.
Trigger: M15 provisional Dow turn. Stop: M15 turn protected swing + 0.3 ATR(H1). Exit: H1 swing trail from +act R.
Adopted: XAUUSD S_ma_prov_buy_mt3_h1a1 (half lot), BTCUSD S_ma_ma_buy_mt3_h1a2 (no new entries on Sat/Sun).
2026-11-07 (docs/OPEN_ITEMS.md, the user's S review and chart checks), XAUUSD from CUTOVER: stop buffer 0.5 ATR(H1) ('mt5'), H1 trail
from +2R ('h1a2'), and skip a setup when the 24 H1 closes before it rose >= 1 ATR(H1) ((C[i-1] - C[i-25]) / ATR14 >= RUN_MAX,
the Q measure: S buys a pullback, so no entry in the middle of a run). 2005-: 626 trades +195R DD 29.7R -> 410 +204R DD 11.8R,
both halves better; P / Q overlap down (monthly corr S-P 0.37 -> 0.14). Entries before CUTOVER keep the old management.
"""
import bisect

import numpy as np
import pandas as pd

from .. import engine as E
from ..core import Frames

STOPS = {'sw3': ('h1swing', 0.3), 'sw8': ('h1swing', 0.8), 'mt3': ('m15turn', 0.3), 'mt5': ('m15turn', 0.5)}
EXITS = {'h1a1': ('h1', 1.0), 'h1a2': ('h1', 2.0), 'h4a1': ('h4', 1.0), 'hyb': ('hyb', 1.0)}
ADOPTED = {'XAUUSD': ('ma', 'prov', 'buy', 'mt5', 'h1a2'), 'BTCUSD': ('ma', 'ma', 'buy', 'mt3', 'h1a2')}
OLD = {'XAUUSD': ('ma', 'prov', 'buy', 'mt3', 'h1a1')}      # before CUTOVER
RUN_MAX = {'XAUUSD': 1.0}
CUTOVER = pd.Timestamp('2026-11-09 00:00')
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


def run(F: Frames, c4, c1, side, st, ex, entry_bar=True, run_max=None):
    cfg = dict(trig='dow', stop=STOPS[st][0], buf=STOPS[st][1], exit=EXITS[ex][0], act=EXITS[ex][1], sw=2.0, win=1)
    if side in ('both_d', 'buy_d'):
        cfg['dside'] = 0      # needs the env filter (not used by the adopted versions)
        raise NotImplementedError('dside filter not ported')
    ev = events(F, c4, c1, side)
    if run_max is not None:
        h1 = F.h1.reset_index(drop=True); C = h1.c.to_numpy(); pc = h1.c.shift()
        A = np.maximum(h1.h - h1.l, np.maximum((h1.h - pc).abs(), (h1.l - pc).abs())).rolling(14).mean().to_numpy()
        pos = {t: i for i, t in enumerate(F.C1)}
        def ok(e):
            i = pos[e['t']]
            return not (i >= 25 and np.isfinite(A[i]) and (C[i - 1] - C[i - 25]) * e['side'] / A[i] >= run_max)
        ev = [e for e in ev if ok(e)]
    return E.run(F, ev, cfg, entry_bar=entry_bar)


def run_adopted(F: Frames, sym, entry_bar=True, cutover=None):
    """The adopted S for `sym`. XAUUSD: entries before CUTOVER are managed by the old setting (OLD), entries from CUTOVER by
    the new one (ADOPTED + RUN_MAX), each from its own full run (like DS's exit switch). cutover=False: the new setting for the
    whole history (research / parity)."""
    new = run(F, *ADOPTED[sym], entry_bar=entry_bar, run_max=RUN_MAX.get(sym))
    cut = CUTOVER if cutover is None else cutover
    if sym not in OLD or cut is False:
        return new
    old = run(F, *OLD[sym], entry_bar=entry_bar)
    parts = []
    for r, after in ((old, False), (new, True)):
        tr = r['trades']
        if isinstance(tr, pd.DataFrame) and len(tr):
            parts.append(tr[[after == (pd.Timestamp(t) >= cut) for t in tr.t]])
    tr = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    opn = [p for p in old['open'] if pd.Timestamp(p['t']) < cut] + [p for p in new['open'] if pd.Timestamp(p['t']) >= cut]
    return dict(trades=tr, open=opn, pending=new['pending'])
