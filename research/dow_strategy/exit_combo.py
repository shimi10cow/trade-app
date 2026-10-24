"""Level + clear MA break: after price has come near an H4/H1 swing level ahead (resistance), exit on a clear break of
H1 SMA75 / M15 SMA200 against the position."""
import sys, bisect
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_ma as M  # noqa: E402
import resist_study as RS  # noqa: E402
S1 = M.S1; T = S1.T; H, L, C, N, COST, BL = M.H, M.L, M.C, M.N, M.COST, M.BL
TR, yrs = S1.load_all()
print(f"基準 合計{sum(t.R.sum() for t in TR.values()):+.1f}R")
for name, mg, nc in (('h1_75', 0.3, 2), ('h1_75', 0.6, 3), ('h1_75', 0.0, 1), ('m15_200', 0.3, 3), ('m15_200', 0.6, 3)):
    for tol in (0.1, 0.3):
        tot = 0; fn = 0; o = 0; nw = 0; b = np.zeros(5); parts = []
        for nm, t in TR.items():
            r = t.R.to_numpy().copy()
            for q, x in enumerate(t.itertuples()):
                s = x.side; ie = min(x.ie, N - 1)
                if x.i0 >= ie:
                    continue
                te = T[x.i0]; k4 = bisect.bisect_right(RS.C4, te) - 1; a4 = RS.A4[k4]; lv = []
                for P, PT, n in ((RS.P4, RS.P4T, 60), (RS.P1, RS.P1T, 120)):
                    j = bisect.bisect_right(PT, te); lv += list(P[max(0, j - n):j])
                lv = np.array(lv); lv = lv[s * (lv - x.entry) > 0.5 * x.risk]
                if not len(lv):
                    continue
                best = np.maximum.accumulate(H[x.i0:ie]) if s == 1 else np.minimum.accumulate(L[x.i0:ie])
                near = np.nonzero(np.any(s * (best[:, None] - lv[None, :]) >= -tol * a4, axis=1))[0]
                if not len(near):
                    continue
                i = M.signal_idx(name, s, x.i0 + near[0], ie, mg, nc)
                if i is not None and x.i0 <= i < ie:
                    nr = s * (C[i] - x.entry) / x.risk - COST / x.risk; fn += 1; o += r[q]; nw += nr; r[q] = nr
            y = yrs[nm]; tot += r.sum(); b += [r[(y >= a) & (y <= z)].sum() for a, z in BL]; parts.append(f'{nm}{r.sum() - t.R.sum():+.0f}')
        print(f'  節目{tol}ATR後に {name} 抜け幅{mg} 連続{nc} 発動{fn:4d}: {o:+6.1f}→{nw:+6.1f} | 合計{tot:+6.1f}R | ' + ' '.join(f'{v:+.0f}' for v in b) + ' | ' + ' '.join(parts), flush=True)
