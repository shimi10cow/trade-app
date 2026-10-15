"""Research-only causal wave filter definitions for EURUSD MA EA.

DO NOT use in live execution without reconciling the original 359/284 counts
and running a full filter-on simulation. Fractal confirmation requires TWO
completed right-hand bars. Signal must not use a pivot until available_at.
"""
from dataclasses import dataclass
from math import isfinite

@dataclass(frozen=True)
class WaveFilterInputs:
    h4_last_impulse: float
    h4_previous_impulse: float
    h1_last_impulse: float
    h1_previous_impulse: float
    h1_close: float
    h1_sma480: float
    h1_atr14: float


def evaluate_filters(x: WaveFilterInputs) -> dict[str, bool]:
    """Filter A: H4 >= 70% and H1 < 75%; B adds SMA480 distance < 12 ATR."""
    values = vars(x).values()
    if not all(isfinite(v) for v in values):
        return {"H4_H1": False, "H4_H1_MA": False}
    if min(x.h4_previous_impulse, x.h1_previous_impulse, x.h1_atr14) <= 0:
        return {"H4_H1": False, "H4_H1_MA": False}
    wave_ok = (x.h4_last_impulse / x.h4_previous_impulse >= .70
               and x.h1_last_impulse / x.h1_previous_impulse < .75)
    distance_atr = abs(x.h1_close - x.h1_sma480) / x.h1_atr14
    return {"H4_H1": wave_ok, "H4_H1_MA": wave_ok and distance_atr < 12.0}

# Research configuration, not a live change:
STUDY_GRID = [(max_p, max_positions, filt)
              for max_p in (3, 4)
              for max_positions in (2, 4)
              for filt in ("OFF", "H4_H1", "H4_H1_MA")]
