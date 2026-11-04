"""R (レンジ) and T / T2 (トレンド・ダウ): the original M15 EA engine (research/core/engine_m15.py) with environment gates,
as in research/dow_strategy/regime_ea.py + regime_ea2.py (2026-10-24).

The engine itself is reused unchanged (it is one causal bar loop over M15); only its data source is replaced by the live
bars. Entry is at the M15 close when the stochastic sequence completes; stop below/above H1 SMA200 (min 10 pips); trail to the
engine's M15 ZigZag swings after +2R or 240 h.
  R2c (EURUSD)       : existing EA with the long-MA filters + range score > 0.7 and within 3 ATR of H4 SMA200
  T1t (EURUSD T2, US30 T): no long-MA filters + H1 major Dow agrees + with the daily side + H4 ER200 > 0.10 + no H4 triangle
  T2 (EURUSD)        : T1t trades minus the H4 'third push with a short correction' ones (axis filter, see wave.py)
Live caveat (R only): the engine's q75 filter compares each signal with ALL earlier qualifying signals since the start of the
data (research: since 2003). A short live window gives a different quantile, so the live R keeps that history (q75_seed).
"""
import bisect
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import TF_LEN, Frames
from ..env import Env

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'research' / 'core'))
import engine_m15 as EM  # noqa: E402

M15 = pd.Timedelta(minutes=15)


def _run_engine(m15, cfg):
    d = m15.rename(columns=dict(t='time', o='open', h='high', l='low', c='close'))[['time', 'open', 'high', 'low', 'close']].copy()
    d['time'] = pd.to_datetime(d.time); d = d.sort_values('time').drop_duplicates('time').reset_index(drop=True)
    old = EM.load_m15
    EM.load_m15 = lambda pair: d.copy()
    try:
        return EM.run_pair('EURUSD', cfg), d      # pair name only sets the pip size (1e-4, the research price space)
    finally:
        EM.load_m15 = old


_SEED = None


def q75_seed(before):
    """R2c (EURUSD) q75 strengths of the research run that happened before `before` (mt5_ea/live/data). The live window
    (1,100 days) is shorter than the research history, so without this the q75 limit would come from fewer points."""
    global _SEED
    if _SEED is None:
        import json
        from pathlib import Path
        f = Path(__file__).resolve().parents[1] / 'data' / 'q75_R2c_EURUSD.json'
        _SEED = json.loads(f.read_text())['points'] if f.exists() else []
    b = str(pd.Timestamp(before))
    out = {1: [], -1: []}
    for t, sd, v in _SEED:
        if t < b:
            out[int(sd)].append(v)
    return out


def gates(F: Frames, env: Env):
    """regime_ea.gate_R / gate_T and regime_ea2 env(...) as callables (t = M15 bar open time, like the engine passes)."""
    R1bars = [b[0] for b in F.R1['bars']]; C1 = F.C1

    def h1_ok(t, s):
        k = bisect.bisect_right(C1, t + M15) - 1
        return k >= 0 and R1bars[k] == ('up' if s == 1 else 'down')

    def feat(t, s):
        k = bisect.bisect_right(env.C4, t) - 1
        return dict(er=env.ER[k], side_h=s * (env.cv[k] - env.S200[k]) / env.A[k], side_d=s * (env.cv[k] - env.S1200[k]) / env.A[k])

    T0 = lambda t, s: h1_ok(t, s) and feat(t, s)['side_d'] > 0 and feat(t, s)['er'] > 0.10
    envf = lambda **kw: (lambda t, s: env.ok(kw, t + M15, s))
    return dict(
        R2c=lambda: EM.Config(extra_filter=envf(env='R2', rs_hi=0.7)),
        T1t=lambda: EM.Config(use_long_ma=False, extra_filter=lambda t, s: T0(t, s) and envf(notri='H4')(t, s)),
    )


def run(F: Frames, key, env=None, m15=None, seed=True):
    """key: 'R2c' or 'T1t'. Uses every M15 bar of F (m15_all) like the research engine run.
    Returns dict(trades, open, pending) in the common format (t = entry bar time, entry at that bar's close)."""
    env = env or Env(F.m15_all)
    src = F.m15_all if m15 is None else m15
    cfg = gates(F, env)[key]()
    if key == 'R2c' and seed:
        cfg.q75_seed = q75_seed(src.t.iat[0])        # live: the research q75 history from before this window
    tr, d = _run_engine(src, cfg)
    if not len(tr):
        return dict(trades=pd.DataFrame(), open=[], pending=[])
    tr = tr.rename(columns=dict(time='t', ExitTime='exit_t', initial_sl='sl0'))
    tr['R'] = tr.R - 1.2e-4 / tr.risk
    last_i = len(d) - 1
    is_open = tr.get('open_end', pd.Series(False, index=tr.index)).fillna(False).astype(bool)
    closed = tr[~is_open & (pd.to_datetime(tr.t) >= F.START)].reset_index(drop=True)
    op = tr[is_open & (pd.to_datetime(tr.t) >= F.START)]
    opened = [dict(r) for _, r in op[op.entry_i < last_i].iterrows()]
    pending = [dict(r, signal_t=r['t']) for _, r in op[op.entry_i == last_i].iterrows()]   # signal on the last closed bar
    return dict(trades=closed, open=opened + pending, pending=pending)
