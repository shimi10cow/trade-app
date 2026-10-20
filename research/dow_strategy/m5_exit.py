"""M5 exits for the 5 EAs (2026-10-20): cut a trade early on an M5 shape instead of waiting for -1R.
Re-simulates each original trade on M5 bars between its entry and its original exit; when the rule fires, exit at that
M5 close (cost 1.2 pip). Rules (long shown; short mirrored) - shape only, no R thresholds:
  m5maj        : M5 major trend turns down (close through the M5 protected low)
  m5maj_uw     : same, only while the trade is under water at that moment (price below entry)
  m5maj_m15    : M5 major turns down while the M15 provisional trend is also down
  m5maj_uw_m15 : both of the above
  m5ll         : price closes below the lowest M5 swing low formed after entry (the trade's own base gave way), under water
  m5ll_m15     : m5ll while M15 provisional trend is down"""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m5_entry as ME  # noqa: E402  (M5 frame, events, pivots, trade loader)
import dow_turn_ea as B  # noqa: E402
T5, H, L, C, N = ME.T5, ME.H, ME.L, ME.C, ME.N
COST = ME.COST; BL = ME.BL
CL15 = pd.DatetimeIndex(B.T15 + pd.Timedelta(minutes=15)); P15 = B.R15['prov_bars']
def m15prov_at(j, d):
    k = CL15.searchsorted(T5[j] + pd.Timedelta(minutes=5), side='right') - 1
    return k >= 0 and P15[k][0] == d
MAJ = {d: ME.EV.get(('major', d), np.array([], int)) for d in ('up', 'down')}
LO = [(a, p) for a, k, p in zip(ME.PA, ME.PK, ME.PP) if k == 'lo']; HI = [(a, p) for a, k, p in zip(ME.PA, ME.PK, ME.PP) if k == 'hi']


def fire(x, rule):
    s = x.side; j0 = T5.searchsorted(x.t0); je = min(T5.searchsorted(x.xt), N - 1)
    if j0 >= je:
        return None
    against = 'down' if s == 1 else 'up'
    if rule.startswith('m5maj'):
        arr = MAJ[against]; k = np.searchsorted(arr, j0)
        while k < len(arr) and arr[k] < je:
            j = arr[k]; k += 1
            if '_uw' in rule and not s * (C[j] - x.entry) < 0:
                continue
            if rule.endswith('_m15') and not m15prov_at(j, against):
                continue
            return j
        return None
    if rule.startswith('m5ll'):
        P = LO if s == 1 else HI; A_ = np.array([a for a, _ in P]); V_ = np.array([p for _, p in P])
        a0 = np.searchsorted(A_, j0); base = None
        for j in range(j0, je):
            while a0 < len(A_) and A_[a0] <= j:
                v = V_[a0]; base = v if base is None else (min(base, v) if s == 1 else max(base, v)); a0 += 1
            if base is not None and s * (C[j] - base) < 0 and s * (C[j] - x.entry) < 0:
                if rule.endswith('_m15') and not m15prov_at(j, against):
                    continue
                return j
        return None
    raise ValueError(rule)


if __name__ == '__main__':
    TR = pd.concat([ME.load(*f) for f in ME.FILES]).reset_index(drop=True)
    TR = TR[(TR.t0 >= T5[0]) & (TR.xt <= T5[-1])].reset_index(drop=True); y = TR.t0.dt.year.to_numpy()
    print(f"元のまま {len(TR)}回 {TR.R.sum():+.1f}R")
    for rule in ('m5maj', 'm5maj_uw', 'm5maj_m15', 'm5maj_uw_m15', 'm5ll', 'm5ll_m15'):
        r = TR.R.to_numpy().copy(); fn = 0; o = 0.0
        for q, x in enumerate(TR.itertuples()):
            j = fire(x, rule)
            if j is not None:
                nr = x.side * (C[j] - x.entry) / x.risk - COST / x.risk; fn += 1; o += r[q]; r[q] = nr
        w = r > 0; b = [r[(y >= a) & (y <= z)].sum() for a, z in BL]
        cut = r[(r < 0)]
        print(f'  {rule:13s} 発動{fn:4d}（元{o:+6.1f}R） 合計{r.sum():+7.1f}R PF{r[w].sum() / -r[~w].sum():.2f} 負けの平均{cut.mean():+.2f}R | ' + ' '.join(f'{v:+.0f}' for v in b)
              + ' | ' + ' '.join(f"{c}:{r[(TR.src == c).to_numpy()].sum() - TR.R[(TR.src == c)].sum():+.0f}" for c in 'RTLAC'), flush=True)
