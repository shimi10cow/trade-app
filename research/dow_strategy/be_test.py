"""Reference only (the user prefers shape over stop moves): once the trade has reached +X R, close at entry if price comes back."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape as S1  # noqa: E402
H, L, N, COST, BL = S1.H, S1.L, S1.N, S1.COST, S1.BL
TR, yrs = S1.load_all()
for X in (1.0, 1.5, 2.0, 3.0):
    tot = 0; b = np.zeros(5); parts = []
    for nm, t in TR.items():
        r = t.R.to_numpy().copy()
        for q, x in enumerate(t.itertuples()):
            ie = min(x.ie, N - 1); s = x.side
            if x.i0 >= ie:
                continue
            fav = (H[x.i0:ie] - x.entry) * s / x.risk if s == 1 else (x.entry - L[x.i0:ie]) / x.risk
            k = np.nonzero(fav >= X)[0]
            if not len(k):
                continue
            j0 = x.i0 + k[0] + 1
            back = np.nonzero((L[j0:ie] <= x.entry) if s == 1 else (H[j0:ie] >= x.entry))[0]
            if len(back):
                r[q] = -COST / x.risk
        y = yrs[nm]; tot += r.sum(); b += [r[(y >= a) & (y <= z)].sum() for a, z in BL]
        w = r > 0; parts.append(f'{nm}{r.sum():+.0f}(PF{r[w].sum() / -r[~w].sum():.2f})')
    print(f'+{X}R到達後に建値 合計{tot:+6.1f}R | ' + ' '.join(f'{v:+.0f}' for v in b) + ' | ' + ' '.join(parts))
