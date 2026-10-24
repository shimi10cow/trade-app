"""Exit when price CLEARLY breaks a key MA against the position (user: not a wick touch, a clear break).
  ma   : H1 SMA75 (judged on H1 closes) | M15 SMA200 (on M15 closes) | M15 SMA75
  how  : close beyond the MA by `mg` x ATR of that timeframe, `nc` consecutive closes beyond
  need : price must have closed on the favourable side of the MA after entry first (a break FROM the right side)
  lvl  : optional - only after price has come near an H4/H1 level (resistance ahead)"""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape as S1  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
B = S1.B; T = S1.T; H, L, C, N, COST, BL = S1.H, S1.L, S1.C, S1.N, S1.COST, S1.BL
m15 = B.m15; A15 = atr(m15)
c15 = pd.Series(C)
h1 = B.h1; c1 = h1.c.to_numpy(float); A1 = atr(h1)
C1 = pd.DatetimeIndex(B.C1)
map1 = np.clip(T.searchsorted(C1) - 1, -1, N - 1)          # M15 bar that ends when each H1 bar closes
SER = {'m15_200': (C, c15.rolling(200).mean().to_numpy(), A15, np.arange(N)),
       'm15_75': (C, c15.rolling(75).mean().to_numpy(), A15, np.arange(N)),
       'h1_75': (c1, h1.c.rolling(75).mean().to_numpy(), A1, map1)}


def signal_idx(name, s, i0, ie, mg, nc):
    cl, ma, a, mp = SER[name]
    if name.startswith('h1'):
        k0 = np.searchsorted(mp, i0); k1 = np.searchsorted(mp, ie)
    else:
        k0, k1 = i0, ie
    if k1 <= k0:
        return None
    rel = s * (cl[k0:k1] - ma[k0:k1])
    fav = np.nonzero(rel > 0)[0]
    if not len(fav):
        return None
    bad = rel < -mg * a[k0:k1]
    run = 0
    for j in range(fav[0], k1 - k0):
        run = run + 1 if bad[j] else 0
        if run >= nc:
            return int(mp[k0 + j])
    return None


def evalrule(TR, yrs, name, mg, nc):
    tot = 0; fn = 0; o = 0; nw = 0; b = np.zeros(5); parts = []
    for nm, t in TR.items():
        r = t.R.to_numpy().copy()
        for q, x in enumerate(t.itertuples()):
            ie = min(x.ie, N - 1)
            if x.i0 >= ie:
                continue
            i = signal_idx(name, x.side, x.i0, ie, mg, nc)
            if i is not None and x.i0 <= i < ie:
                nr = x.side * (C[i] - x.entry) / x.risk - COST / x.risk
                fn += 1; o += r[q]; nw += nr; r[q] = nr
        y = yrs[nm]; tot += r.sum(); b += [r[(y >= a) & (y <= z)].sum() for a, z in BL]
        w = r > 0; parts.append(f'{nm}{r.sum() - t.R.sum():+.0f}(PF{r[w].sum() / -r[~w].sum():.2f})')
    return tot, fn, o, nw, b, parts


if __name__ == '__main__':
    TR, yrs = S1.load_all()
    print(f"基準 合計{sum(t.R.sum() for t in TR.values()):+.1f}R")
    for name in ('h1_75', 'm15_200', 'm15_75'):
        for mg in (0.0, 0.3, 0.6):
            for nc in (1, 2, 3):
                tot, fn, o, nw, b, parts = evalrule(TR, yrs, name, mg, nc)
                print(f'  {name:7s} 抜け幅{mg}ATR 連続{nc}本 発動{fn:4d}: {o:+6.1f}→{nw:+6.1f} | 合計{tot:+6.1f}R | ' + ' '.join(f'{v:+.0f}' for v in b) + ' | ' + ' '.join(parts), flush=True)
