"""Break EA from the user's 'bo' marks (2026-10-22): the turn starts before SMA20/75 crosses.
Setup: H1 provisional Dow turns (higher low / double bottom; PROV_START or REVERSAL) while H1 SMA20/75 still points the
other way (and, optionally, the H4 provisional trend already agrees). Trigger: at once ('now') or the next M15 provisional
turn in the same direction within 24h ('dow'). Stop: the provisional protected low ('ref') or the last H1 swing,
+ 0.3 ATR(H1). Exit: H1 swing trail from +1R. Writes results/bo/BO2_<...>.csv."""
import sys, os, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'bo'; OUT.mkdir(parents=True, exist_ok=True)
X.add_trigger('now', lambda: {d: list(range(X.N)) for d in ('up', 'down')})
h1 = B.h1.reset_index(drop=True); M20 = h1.c.rolling(20).mean().to_numpy(); M75 = h1.c.rolling(75).mean().to_numpy()
P4 = [b[0] for b in B.R4['prov_bars']]
import bisect
def events(h4='any', win=24):
    ev = []
    for e in B.R1['prov_events']:
        if e['action'] not in ('REVERSAL', 'PROV_START'): continue
        i = e['idx']; to = e['to']; s = 1 if to == 'up' else -1
        if not np.isfinite(M75[i]) or np.sign(M20[i] - M75[i]) != -s: continue      # before the cross
        ref = B.R1['prov_bars'][i][1]
        t = B.C1[i]
        if h4 == 'same':
            k4 = bisect.bisect_right(B.C4, t) - 1
            if k4 < 0 or P4[k4] != to: continue
        ev.append(dict(t=t, side=s, tag='bo2', ref=ref, win=win))
    return ev
def run1(c):
    h4, trig, stop = c
    tr = X.run(events(h4), dict(trig=trig, stop=stop, buf=0.3, exit='h1', act=1.0, win=24))
    name = f'BO2_{h4}_{trig}_{stop}'; tr.to_csv(OUT / f'{name}.csv', index=False); return name, len(tr)
if __name__ == '__main__':
    G = list(itertools.product(('any', 'same'), ('now', 'dow'), ('ref', 'h1swing')))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for n, k in p.imap_unordered(run1, G): print(n, k, flush=True)
