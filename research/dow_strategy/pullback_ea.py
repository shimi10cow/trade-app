"""Pattern B (user's 'pullback to the H4 protected level', 9 of 22 model trades), 2026-10-19.

  context : H4 major trend d (optionally H4 stage >= 1 = mid-trend)
  setup   : price comes back to within `band` x ATR(H4) of the H4 protected level (押し安値/戻り高値)
            from the trend side; one setup per visit (re-armed after price leaves 2 x band)
  trigger : M15 provisional turn to d after the touch (same machinery as retest_ea)
  stop    : beyond the M15 swing + buf x ATR7(H1); exit: H1 trail after 1R | fixed target
Periods: develop 2020-2024, check 2025, 2026. Usage: EA_M15_CACHE=<csv> python dow_strategy/pullback_ea.py [names]
"""
import bisect
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import retest_ea as RT  # noqa: E402
import dow_turn_ea as B  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from long_features import stage_arrays  # noqa: E402

ST4 = stage_arrays(B.R4, len(B.h4))


def pullback_setups(cfg):
    res = []
    M = RT.M15T
    C4 = B.C4
    armed = {1: True, -1: True}
    k_prev = -1
    for i in range(len(M)):
        k = bisect.bisect_right(C4, M[i]) - 1             # last closed H4 bar at this M15 bar's open
        if k < 0:
            continue
        tr, prot = B.R4['bars'][k]
        if tr is None or prot is None:
            continue
        s = 1 if tr == 'up' else -1
        if cfg.get('min_stage') is not None and ST4[k] < cfg['min_stage']:
            continue
        if cfg.get('max_stage') is not None and ST4[k] > cfg['max_stage']:
            continue
        band = cfg['band'] * RT.A4[k]
        near = (B.l[i] <= prot + band) if s == 1 else (B.h[i] >= prot - band)
        far = (B.l[i] > prot + 2 * band) if s == 1 else (B.h[i] < prot - 2 * band)
        if far:
            armed[s] = True
        if near and armed[s] and s * (B.c[i] - prot) > 0:
            armed[s] = False
            res.append((i, i + cfg['win'] * 4, 'up' if s == 1 else 'down', prot, 'H4', i))
    return res


BASE = dict(win=48, tol=0.3, buf=1.0, band=1.0)
CFGS = [
    dict(BASE, name='P1 押し安値±1ATR'),
    dict(BASE, name='P2 ±0.5ATR', band=0.5),
    dict(BASE, name='P3 ±2ATR', band=2.0),
    dict(BASE, name='P4 P1＋MA', ma=True),
    dict(BASE, name='P5 P1・段階1以上', min_stage=1),
    dict(BASE, name='P6 P1・段階0〜2', max_stage=2),
    dict(BASE, name='P7 P1・固定3R', tp=3.0),
    dict(BASE, name='P8 P1＋MA・固定3R', ma=True, tp=3.0),
]


def run(cfg):
    RT.setups = lambda c: pullback_setups(c)
    return RT.run(cfg)


if __name__ == '__main__':
    pick = [c for c in CFGS if not sys.argv[1:] or c['name'].split()[0] in sys.argv[1:]]
    with Pool(4) as pool:
        for name, tr in pool.imap(run, pick):
            y = tr.t.dt.year
            tr.to_csv(B.HERE / 'results' / f"pullback_{name.split()[0]}.csv", index=False)
            print(f"{name}\n   開発2020-24 {B.stats(tr.R[(y >= 2020) & (y <= 2024)].to_numpy())}"
                  f"\n   確認2025    {B.stats(tr.R[y == 2025].to_numpy())}\n   2026        {B.stats(tr.R[y == 2026].to_numpy())}"
                  f"\n   SL中央値{tr.risk.median() / B.PIP:.0f}pips  {B.recall(tr)}", flush=True)
