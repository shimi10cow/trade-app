"""H4 opening / slope gate for some existing EAs (docs/EA_PLAN_20261102.md §2, RESEARCH_LOG §143-§147, 2026-11-02).

  'open'  : enter only while (H4 SMA20 - SMA75) x side / ATR14(H4) < 2.5   -> C@USDJPY, T@US30, Q@XAGUSD, Q@US30, DS@JP225
  'slope' : enter only while (H4 SMA75 - 10 bars earlier) x side / ATR14(H4) < 0.35   -> R@EURUSD
Both from the last H4 bar closed by the trade's time (research trendlab/h4f.py on the trade list's 't'). The research estimate
applied the condition to the EA's finished trade list, so the gate does the same: it drops trades / open positions / pending
entries whose entry fails it, and leaves the EA's own logic untouched.
Time used: 't' of the trade (engine EAs: the entry bar; engine_m15 EAs: the signal bar); a pending entry of an engine EA has no
't' yet, so its entry bar (signal bar + 15 min) is used.
"""
import pandas as pd

from .nt import h4_shape

LIMIT = {'open': 2.5, 'slope': 0.35}
M15 = pd.Timedelta(minutes=15)


def _when(p):
    if 't' in p and p['t'] is not None and not pd.isna(p['t']):
        return pd.Timestamp(p['t'])
    return pd.Timestamp(p['signal_t']) + M15


def gate(fn, kind):
    """Wrap an EA run(F, env) so that it only keeps entries passing the H4 gate."""
    lim = LIMIT[kind]; col = 0 if kind == 'open' else 1

    def run(F, env):
        r = fn(F, env); shape = h4_shape(F.m15_all)
        ok = lambda t, s: shape(t, int(s))[col] < lim
        tr = r['trades']
        if isinstance(tr, pd.DataFrame) and len(tr):
            tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]
            tr = tr[[ok(t, s) for t, s in zip(tr[tc], tr['side'])]].reset_index(drop=True)
        return dict(r, trades=tr, open=[p for p in r['open'] if ok(_when(p), p['side'])],
                    pending=[p for p in r['pending'] if ok(_when(p), p['side'])])
    return run
