"""Exit by shape v2 (closer to the user's picture): sell at B -> price comes down to near A (= C, reached >= frac of the
way from entry to A) but does not get past A by more than ext*risk -> the red line is the M15 swing high formed AFTER C
(no new low since) -> close when a M15 close goes through it."""
import sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape as S1  # noqa: E402
PA, PI, PK, PP, H, L, C, N, COST, BL = S1.PA, S1.PI, S1.PK, S1.PP, S1.H, S1.L, S1.C, S1.N, S1.COST, S1.BL


AWIN = 0          # 0: last M15 swing before entry; >0: extreme of the last AWIN M15 bars (the first wave's low)


def shape_exit(x, frac, ext, minbars=0):
    s = x.side; i0 = x.i0; ie = min(x.ie, N - 1)
    if i0 >= ie:
        return None
    if AWIN:
        A = L[max(0, i0 - AWIN):i0].min() if s == -1 else H[max(0, i0 - AWIN):i0].max()
    else:
        k = np.searchsorted(PA, i0) - 1; fk = 'lo' if s == -1 else 'hi'
        while k >= 0 and PK[k] != fk:
            k -= 1
        if k < 0:
            return None
        A = PP[k]
    dA = s * (A - x.entry)
    if dA <= 0:
        return None
    ok = 'hi' if s == -1 else 'lo'
    a, b = np.searchsorted(PA, i0), np.searchsorted(PA, ie)
    cand = [j for j in range(a, b) if PK[j] == ok and PI[j] >= i0]
    for n, j in enumerate(cand):
        seg = L[i0:PA[j] + 1] if s == -1 else H[i0:PA[j] + 1]
        ce = int(np.argmin(seg) if s == -1 else np.argmax(seg)) + i0; cpx = L[ce] if s == -1 else H[ce]
        if PI[j] <= ce:                                       # red line must be formed after C
            continue
        if s * (cpx - x.entry) < frac * dA or s * (A - cpx) < -ext * x.risk:
            continue                                          # did not reach the A zone, or broke clearly past A
        if PI[j] - ce < minbars:
            continue
        red = PP[j]; st = PA[j]; en = PA[cand[n + 1]] if n + 1 < len(cand) else ie
        for i in range(st, en):
            if (L[i] < cpx) if s == -1 else (H[i] > cpx):     # new extreme -> this red line is void
                break
            if (C[i] > red) if s == -1 else (C[i] < red):
                return i
    return None


if __name__ == '__main__':
    TR, yrs = S1.load_all()
    print(f"基準 合計{sum(t.R.sum() for t in TR.values()):+.1f}R")
    import itertools
    for AWIN, frac, ext, mb in itertools.product((96, 192, 384), (0.7, 0.9), (0.0, 0.3), (0, 8)):
        if True:
            if True:
                tot = 0; fn = 0; o = 0; nw = 0; b = np.zeros(5); parts = []
                for nm, t in TR.items():
                    r = t.R.to_numpy().copy()
                    for q, x in enumerate(t.itertuples()):
                        i = shape_exit(x, frac, ext, mb)
                        if i is not None:
                            nr = x.side * (C[i] - x.entry) / x.risk - COST / x.risk
                            fn += 1; o += r[q]; nw += nr; r[q] = nr
                    y = yrs[nm]; tot += r.sum(); b += [r[(y >= a) & (y <= z)].sum() for a, z in BL]
                    w = r > 0; parts.append(f'{nm}{r.sum() - t.R.sum():+.0f}')
                print(f'  A窓{AWIN:3d} A到達{frac:.1f} A超え許容{ext:.1f}R C後{mb:2d}本 発動{fn:4d}: {o:+6.1f}→{nw:+6.1f} | 合計{tot:+6.1f}R | ' + ' '.join(f'{v:+.0f}' for v in b) + ' | ' + ' '.join(parts), flush=True)
