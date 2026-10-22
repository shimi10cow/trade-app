"""Q: breakout from a quiet market (2026-10-22, from the finding that entries in a quiet market win more on trend instruments).
Setup at an H1 close: ATR14(H1) is below `vq` x its median of the past 1000 H1 bars, and the close breaks the highest high
(buy) / lowest low (sell) of the previous `n` H1 bars. Direction filter `d`: 'any', 'h4' (H4 provisional trend agrees),
'ma' (H1 SMA75 rising for buys / falling for sells). Trigger: 'now' (next M15 open) or 'dow' (M15 provisional turn within 12h).
Stop: 'rng' = the other side of the n-bar range is too wide, so the range middle ('mid') or the last H1 swing ('h1swing'), +0.3 ATR.
Exit: swing trail from +1R on H1 or H4. Writes results/q/Q_<...>.csv"""
import sys, os, itertools, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'q'; OUT.mkdir(parents=True, exist_ok=True)
X.add_trigger('now', lambda: {d: list(range(X.N)) for d in ('up', 'down')})
h1 = B.h1.reset_index(drop=True)
pc = h1.c.shift(); tr = np.maximum(h1.h - h1.l, np.maximum((h1.h - pc).abs(), (h1.l - pc).abs()))
ATR = tr.rolling(14).mean(); VR = (ATR / ATR.rolling(1000, min_periods=300).median()).to_numpy()
M75 = h1.c.rolling(75).mean().to_numpy(); P4 = [b[0] for b in B.R4['prov_bars']]
C = h1.c.to_numpy()
def events(vq, n, d):
    HH = h1.h.rolling(n).max().shift(1).to_numpy(); LL = h1.l.rolling(n).min().shift(1).to_numpy()
    ev = []; last = {1: -99, -1: -99}
    for i in range(1100, len(h1)):
        if not (VR[i] < vq): continue
        for s, brk in ((1, C[i] > HH[i]), (-1, C[i] < LL[i])):
            if not brk or i - last[s] < n: continue           # one setup per side per range
            t = B.C1[i]
            if d == 'h4':
                k4 = bisect.bisect_right(B.C4, t) - 1
                if k4 < 0 or P4[k4] != ('up' if s == 1 else 'down'): continue
            if d == 'ma' and not (np.isfinite(M75[i - 5]) and s * (M75[i] - M75[i - 5]) > 0): continue
            last[s] = i
            ev.append(dict(t=t, side=s, tag='q', ref=(HH[i] + LL[i]) / 2, win=12))
    return ev
def run1(c):
    vq, n, d, trig, stop, ex = c
    tr = X.run(events(vq, n, d), dict(trig=trig, stop=stop, buf=0.3, exit=ex, act=1.0, win=12))
    name = f'Q_{vq}_{n}_{d}_{trig}_{stop}_{ex}'; tr.to_csv(OUT / f'{name}.csv', index=False)
    r = tr.R if len(tr) else pd.Series(dtype=float)
    return name, len(tr), r.sum()
if __name__ == '__main__':
    G = list(itertools.product((0.8, 1.0), (24, 48), ('any', 'h4', 'ma'), ('now', 'dow'), ('ref', 'h1swing'), ('h1', 'h4')))
    with Pool(int(os.environ.get('NPROC', '2'))) as p:
        for n, k, r in p.imap_unordered(run1, G): print(n, k, round(r, 1), flush=True)
