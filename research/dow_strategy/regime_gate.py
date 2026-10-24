"""Causal regime measure: mean follow-through (ATR, 30 H4 bars) of the last N H4 major reversals / breakouts,
using only events whose 30-bar outcome is already known at time t."""
import bisect, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load
from env_recognition.ea_api import TF_LEN
from env_recognition import dow_trend
from env_recognition.pivots import atr
_h4 = load('H4', 'long').reset_index(drop=True); _r = dow_trend.run(_h4, 'H4'); _A = atr(_h4); _c = _h4.c.to_numpy()
_C4 = list(pd.to_datetime(_h4.t) + TF_LEN['H4']); HZ = 30
EV = {'REVERSAL': [], 'BREAKOUT': []}
for e in _r['events']:
    if e.get('machine') != 'major' or e['action'] not in EV:
        continue
    k = e['idx']
    if k + HZ >= len(_c):
        continue
    s = 1 if (e.get('to') or e['trend']) == 'up' else -1
    EV[e['action']].append((_C4[k + HZ], s * (_c[k + HZ] - _c[k]) / _A[k]))
for a in EV:
    EV[a].sort()
_T = {a: [x[0] for x in L] for a, L in EV.items()}


def regime(t, N=40):
    out = {}
    for a, L in EV.items():
        j = bisect.bisect_right(_T[a], t); w = [x[1] for x in L[max(0, j - N):j]]
        out[a] = float(np.mean(w)) if len(w) >= N // 2 else np.nan
    return out
