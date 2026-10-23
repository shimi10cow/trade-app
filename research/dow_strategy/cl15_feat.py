"""C (M15 correction line breakout) split by the strength of the line (user, 2026-10-23: a correction line touched 1-3
times = positions built up -> its break runs further; even without touches, enough small Dow swings inside and enough time
(横軸) make the break stronger). Same events and settings as the adopted C (md4tri). Features of each line at its break:
  dur   : bars from the correction's start (A) to the break
  npiv  : confirmed M15 swing highs (for a buy; lows for a sell) between A and the break = small Dow swings inside
  touch : bars after the 2nd point whose high (low) came within 0.15 ATR(M15) of the line before the break
  slope : |line slope| per bar in ATR(M15)
Writes results/step2/C_feat.csv (trades with the features)."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
import m15_corr_lines as M  # noqa: E402
B = X.B
piv = {}
for e in B.R15['pivot_events']: piv[e['id']] = e
P = sorted((e['idx'], e['kind'], e['available_idx']) for e in piv.values())
ev = []
for ia, pa, ib, pb, cr, en, kind, broken, ll, h4w in M.lines():
    if not broken or en is None: continue
    s = 1 if kind == 'hi' else -1
    seg = B.l[ia:en + 1] if s == 1 else B.h[ia:en + 1]; ref = seg.min() if s == 1 else seg.max()
    a = M.A15[en] if np.isfinite(M.A15[en]) and M.A15[en] > 0 else M.A15[ia]
    sl = (pb - pa) / (ib - ia); line = lambda j: pa + sl * (j - ia)
    npiv = sum(1 for (ix, k, av) in P if k == kind and ia < ix < en and av <= en)
    ext = B.h if kind == 'hi' else B.l
    touch = int(sum(1 for j in range(ib + 1, en) if abs(ext[j] - line(j)) <= 0.15 * a))
    ev.append(dict(t=X.CL15[en], side=s, ref=ref, win=4, tag=f'{en - ia}|{npiv}|{touch}|{abs(sl) / a:.4f}'))
tr = X.run(ev, dict(trig='dow', stop='m15turn', buf=1.0, exit='h1', act=1.0, dside=0, maxdev=4, notri='H4'))
f = tr.tag.str.split('|', expand=True).astype(float); tr['dur'], tr['npiv'], tr['touch'], tr['slope'] = f[0], f[1], f[2], f[3]
tr.to_csv(B.HERE / 'results' / 'step2' / 'C_feat.csv', index=False)
print(len(ev), 'lines broken', len(tr), 'trades', round(tr.R.sum(), 1))
