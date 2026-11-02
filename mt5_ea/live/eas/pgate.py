"""Gates taken from the P (new trend) EA's entry conditions, for some existing EAs (RESEARCH_LOG §158, 2026-11).

  'ext'  : skip an entry when the H1 SMA20/75 trend it follows has already moved more than 6 ATR(H1) since it began
           (nt._impulse, measured at the trade's time). Entries against the H1 trend / in its first hour have no value and pass.
           -> C@EURUSD (the line break after a long run is a last push: removed trades -0.22 / -0.35R in the two halves),
              A@EURUSD (late return moves: removed trades about 0R)
  'band' : skip an entry when the last 24 H1 bars bounced off an H4 / D1 level and the close is back on the trade side
           (nt._levels, at the trade's time + 15 min, like P). -> T@US30 (same engine as P; removed trades win 28%, -0.01 / -0.32R)
Applied like eas/h4gate.py: the EA runs unchanged and trades / open positions / pending entries failing the gate are dropped.
"""
import numpy as np
import pandas as pd

from . import nt as NT
from .h4gate import _when

M15 = pd.Timedelta(minutes=15)
IMPULSE_MAX = 6.0


def _impulse_fn(F):
    d = F.m15_all.rename(columns=dict(t='time', o='open', h='high', l='low', c='close'))[['time', 'open', 'high', 'low', 'close']].copy()
    d['time'] = pd.to_datetime(d.time); d = d.sort_values('time').drop_duplicates('time').reset_index(drop=True)
    old = NT.EM.load_m15; NT.EM.load_m15 = lambda pair: d.copy()
    try:
        m, h1, _, _, _ = NT.EM.build_features('EURUSD')
    finally:
        NT.EM.load_m15 = old
    return NT._impulse(m, h1)


def gate(fn, kind):
    def run(F, env):
        r = fn(F, env)
        if kind == 'ext':
            imp = _impulse_fn(F)
            ok = lambda t, s: not (imp(t, int(s)) > IMPULSE_MAX)            # NaN (not measurable) passes
        else:
            lev = NT._levels(F)
            ok = lambda t, s: not lev(pd.Timestamp(t) + M15, int(s))[0]
        tr = r['trades']
        if isinstance(tr, pd.DataFrame) and len(tr):
            tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]
            tr = tr[[ok(t, s) for t, s in zip(tr[tc], tr['side'])]].reset_index(drop=True)
        return dict(r, trades=tr, open=[p for p in r['open'] if ok(_when(p), p['side'])],
                    pending=[p for p in r['pending'] if ok(_when(p), p['side'])])
    return run
