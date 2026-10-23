"""Is the profit just luck / market drift? (user, 2026-10-23). Random entries through the common engine (ea_core), same
stop and exit style as most adopted EAs: enter at the next M15 open, stop beyond the last confirmed H1 swing + 0.3 ATR(H1),
H1 swing trail from +1R, one position per side.
  rand  : random time, random side (50/50)         -> what the stop/exit alone gives
  trend : random time, side = H4 major Dow trend   -> what 'just follow the H4 trend' gives
20 seeds each, ~150 setups a year. Writes results/bench/<mode>_<seed>.csv and prints the per-trade mean R by half."""
import sys, os
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'bench'; OUT.mkdir(parents=True, exist_ok=True)
X.add_trigger('now', lambda: {d: list(range(X.N)) for d in ('up', 'down')})
CL = pd.DatetimeIndex(X.CL15); ok = np.nonzero(CL >= B.START)[0]
C4 = pd.DatetimeIndex(B.C4); TR4 = [b[0] for b in B.R4['bars']]
years = (CL[-1] - B.START).days / 365.25


def run1(job):
    mode, seed = job
    rng = np.random.default_rng(seed); k = rng.choice(ok, int(150 * years), replace=False); k.sort()
    ev = []
    for i in k:
        t = CL[i]
        if mode == 'rand': s = 1 if rng.random() < 0.5 else -1
        else:
            j = C4.searchsorted(t, 'right') - 1
            tr = TR4[j] if j >= 0 else None
            if tr not in ('up', 'down'): continue
            s = 1 if tr == 'up' else -1
        ev.append(dict(t=t - pd.Timedelta('1min'), side=s, tag=mode, win=1))
    tr = X.run(ev, dict(trig='now', stop='h1swing', buf=0.3, exit='h1', act=1.0, win=1))
    tr.to_csv(OUT / f'{mode}_{seed}.csv', index=False)
    y = pd.to_datetime(tr.t).dt.year
    return mode, seed, len(tr), tr.R[y <= 2015].mean(), tr.R[y >= 2016].mean()


if __name__ == '__main__':
    jobs = [(m, s) for m in ('rand', 'trend') for s in range(20)]
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for r in p.imap_unordered(run1, jobs): print(*r, flush=True)
