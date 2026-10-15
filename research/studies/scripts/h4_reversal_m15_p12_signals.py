"""Standalone causal M15 Stochastic P1/P2 signal detector for H4 reversal research.

Research-only. No H4 level gate, execution, SL, or performance claim here.
Matches the three-stage signal state machine in research/core/engine_m15.py.
The canonical core currently calculates raw(14)->SMA(3)->SMA(5).
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

@dataclass(frozen=True)
class StochSettings:
    lookback: int = 14
    k_smoothing: int = 3
    d_smoothing: int = 5
    oversold: float = 20.
    overbought: float = 80.

def calculate_stochastic(bars: pd.DataFrame, cfg: StochSettings = StochSettings()):
    lo = bars["low"].rolling(cfg.lookback).min()
    hi = bars["high"].rolling(cfg.lookback).max()
    raw = (100 * (bars["close"] - lo) / (hi - lo).replace(0, np.nan))
    k = raw.rolling(cfg.k_smoothing).mean()
    d = k.rolling(cfg.d_smoothing).mean()
    return k, d

def completed_signals(bars: pd.DataFrame, regime_id, regime_side, cfg: StochSettings = StochSettings()):
    """Return signals after each M15 bar closes. regime_id/side must be causal H4 values
    available at that M15 close. P is counted on completed signals, before level gating.
    Output: index, side (+1/-1), point (P1/P2/...), regime_id.
    """
    if len(bars) != len(regime_id) or len(bars) != len(regime_side):
        raise ValueError("bars and regime arrays must have equal length")
    k, d = calculate_stochastic(bars, cfg)
    states = {1: 0, -1: 0}
    counts = {1: 0, -1: 0}
    previous_regime = None
    previous_k = previous_d = np.nan
    out = []
    for i in range(len(bars)):
        rid = regime_id[i]
        side_regime = regime_side[i]
        if rid != previous_regime:
            states = {1: 0, -1: 0}
            counts = {1: 0, -1: 0}
            previous_regime = rid
        K, D = k.iloc[i], d.iloc[i]
        completed = []
        if np.isfinite(K) and np.isfinite(D):
            if states[1] == 0 and K < cfg.oversold:
                states[1] = 1
            elif states[1] == 1 and np.isfinite(previous_k) and np.isfinite(previous_d) and previous_k <= previous_d and K > D:
                states[1] = 2
            elif states[1] == 2 and np.isfinite(previous_k) and previous_k <= cfg.oversold and K > cfg.oversold:
                states[1] = 0
                completed.append(1)
            if states[-1] == 0 and K > cfg.overbought:
                states[-1] = 1
            elif states[-1] == 1 and np.isfinite(previous_k) and np.isfinite(previous_d) and previous_k >= previous_d and K < D:
                states[-1] = 2
            elif states[-1] == 2 and np.isfinite(previous_k) and previous_k >= cfg.overbought and K < cfg.overbought:
                states[-1] = 0
                completed.append(-1)
        previous_k, previous_d = K, D
        for side in completed:
            if side != side_regime:
                continue
            counts[side] += 1
            out.append({"bar_index": i, "side": side, "point": counts[side], "regime_id": rid})
    return pd.DataFrame(out, columns=["bar_index", "side", "point", "regime_id"])
