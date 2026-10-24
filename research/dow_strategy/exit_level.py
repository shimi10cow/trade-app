"""Exit = level + shape: once price has come within tol x ATR(H4) of an H4/H1 swing level (known at entry, beyond entry in the
trade direction), the next M15 structure turn against the position (provisional or major) closes the trade.
No R threshold anywhere: only 'reached a level' and 'shape turned'."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape as S1  # noqa: E402
import exit_rules as E1  # noqa: E402
import resist_study as RS  # noqa: E402
B = S1.B; T = S1.T; H, L, C, N, COST, BL = S1.H, S1.L, S1.C, S1.N, S1.COST, S1.BL
EV = E1.EV


def run(TR, yrs, tfs, kind, tol, minlv):
    tot = 0; fn = 0; o = 0; nw = 0; b = np.zeros(5); parts = []
    for nm, t in TR.items():
        r = t.R.to_numpy().copy()
        for q, x in enumerate(t.itertuples()):
            s = x.side; ie = min(x.ie, N - 1)
            if x.i0 >= ie:
                continue
            te = T[x.i0]; k4 = bisect.bisect_right(RS.C4, te) - 1; a4 = RS.A4[k4]
            lv = []
            for P, PT, n in ((RS.P4, RS.P4T, 60),) if tfs == 'H4' else ((RS.P4, RS.P4T, 60), (RS.P1, RS.P1T, 120)):
                j = bisect.bisect_right(PT, te); lv += list(P[max(0, j - n):j])
            lv = np.array(lv); d = s * (lv - x.entry)
            lv = lv[d > minlv * x.risk]
            if not len(lv):
                continue
            best = (np.maximum.accumulate(H[x.i0:ie]) if s == 1 else np.minimum.accumulate(L[x.i0:ie]))
            near = np.nonzero(np.any(s * (best[:, None] - lv[None, :]) >= -tol * a4, axis=1))[0]
            if not len(near):
                continue
            it = x.i0 + near[0]
            arr = EV.get((kind, 'down' if s == 1 else 'up'), np.array([], int))
            j = np.searchsorted(arr, it)
            if j < len(arr) and arr[j] < ie:
                i = arr[j]; nr = s * (C[i] - x.entry) / x.risk - COST / x.risk
                fn += 1; o += r[q]; nw += nr; r[q] = nr
        y = yrs[nm]; tot += r.sum(); b += [r[(y >= a) & (y <= z)].sum() for a, z in BL]
        w = r > 0; parts.append(f'{nm}{r.sum() - t.R.sum():+.0f}')
    return tot, fn, o, nw, b, parts


if __name__ == '__main__':
    TR, yrs = S1.load_all()
    print(f"基準 合計{sum(t.R.sum() for t in TR.values()):+.1f}R")
    for tfs in ('H4', 'H4H1'):
        for kind in ('prov', 'major'):
            for tol in (0.1, 0.3):
                for minlv in (0.5, 1.0):
                    tot, fn, o, nw, b, parts = run(TR, yrs, tfs, kind, tol, minlv)
                    print(f'  節目{tfs:5s} 形={kind:5s} 近さ{tol}ATR 節目は{minlv}R以上先 発動{fn:4d}: {o:+6.1f}→{nw:+6.1f} | 合計{tot:+6.1f}R | ' + ' '.join(f'{v:+.0f}' for v in b) + ' | ' + ' '.join(parts), flush=True)
