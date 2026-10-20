"""Exit by shape (user's picture, 2026-10-20). Short example (mirror for long):
  A = last M15 low confirmed before entry (the first low), entry = sell at the pullback high B.
  If price fails to extend clearly beyond A (lowest low since entry > A - ext*risk), and then closes above the most recent
  M15 swing high formed AFTER entry (the red line: the stall's last lower high), close the trade at that close.
  Not a plain 'M15 Dow turn' exit: it fires only when the trade failed to extend past A.
Variants: ext (how far past A still counts as 'failed'), lh (red line must be below entry = a lower high), mfe cap."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_rules as E1  # noqa: E402
B = E1.B; T = E1.T; H, L, C = E1.H, E1.L, E1.C; N = E1.N; COST = E1.COST
PV = sorted(((e['available_idx'], e['idx'], e['kind'], e['price']) for e in B.R15['pivot_events'] if e.get('action', 'confirm') == 'confirm'))
PA = np.array([p[0] for p in PV]); PI = np.array([p[1] for p in PV]); PK = np.array([p[2] for p in PV]); PP = np.array([p[3] for p in PV])
BL = ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))


def shape_exit(x, ext, lh, mfecap):
    s = x.side; i0 = x.i0; ie = min(x.ie, N - 1)
    if i0 >= ie:
        return None
    k = np.searchsorted(PA, i0) - 1                                   # pivots available before entry
    fk = 'lo' if s == -1 else 'hi'
    while k >= 0 and PK[k] != fk:
        k -= 1
    if k < 0:
        return None
    A = PP[k]
    ok = 'hi' if s == -1 else 'lo'                                    # red line = opposite swing formed after entry
    a, b = np.searchsorted(PA, i0), np.searchsorted(PA, ie)
    cand = [j for j in range(a, b) if PK[j] == ok and PI[j] >= i0]
    for n, j in enumerate(cand):
        red = PP[j]
        if lh and s * (x.entry - red) < 0:                            # red line must be better than entry
            continue
        st = PA[j]; en = PA[cand[n + 1]] if n + 1 < len(cand) else ie
        seg = C[st:en]
        hit = np.nonzero(seg > red)[0] if s == -1 else np.nonzero(seg < red)[0]
        if not len(hit):
            continue
        i = st + hit[0]
        ext_px = L[i0:i + 1].min() if s == -1 else H[i0:i + 1].max()
        if s * (A - ext_px) > ext * x.risk:                           # extended past A -> trend worked, leave it to the trail
            return None
        mfe = s * (ext_px - x.entry) / x.risk
        if mfe >= mfecap:
            return None
        return i
    return None


def run(TR, yrs, ext, lh, mfecap):
    tot = 0; fn = 0; o = 0; nw = 0; b = np.zeros(5); parts = []; rr = {}
    for n, t in TR.items():
        r = t.R.to_numpy().copy()
        for q, x in enumerate(t.itertuples()):
            i = shape_exit(x, ext, lh, mfecap)
            if i is not None:
                nr = x.side * (C[i] - x.entry) / x.risk - COST / x.risk
                fn += 1; o += r[q]; nw += nr; r[q] = nr
        y = yrs[n]; tot += r.sum(); b += [r[(y >= a) & (y <= z)].sum() for a, z in BL]
        w = r > 0; parts.append(f'{n}{r.sum() - t.R.sum():+.0f}(PF{r[w].sum() / -r[~w].sum():.2f})'); rr[n] = r
    return tot, fn, o, nw, b, parts, rr


def load_all():
    TR = {n: E1.load(n, f) for n, f in E1.FILES}; yrs = {}
    for n, t in TR.items():
        y = pd.DatetimeIndex(np.asarray(T)[t.i0.clip(upper=N - 1).to_numpy()]).year.to_numpy()
        TR[n] = t[y >= 2005].reset_index(drop=True); yrs[n] = y[y >= 2005]
    return TR, yrs


if __name__ == '__main__':
    TR, yrs = load_all()
    print(f"基準 合計{sum(t.R.sum() for t in TR.values()):+.1f}R")
    print('ext=A をどこまで割っても「割れきれず」とみなすか(R) / lh=赤ラインがエントリーより有利側のみ / mfe上限')
    for ext in (0.0, 0.3, 0.5, 1.0):
        for lh in (0, 1):
            for cap in (1.0, 99):
                tot, fn, o, nw, b, parts, _ = run(TR, yrs, ext, lh, cap)
                print(f'  ext{ext:.1f} lh{lh} mfe<{cap:<4} 発動{fn:4d}: {o:+7.1f}→{nw:+7.1f} | 合計{tot:+6.1f}R | ' + ' '.join(f'{v:+.0f}' for v in b) + ' | ' + ' '.join(parts), flush=True)
