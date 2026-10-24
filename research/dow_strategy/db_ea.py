"""Double bottom / double top turn (user image for USDJPY, 2026-10-21; buy shown, sell mirrored).
At a provisional turn up made before the major trend turned (as J): L2 = the provisional protected low (the new low that
held), L1 = the previous confirmed swing low (the trend's low). Double bottom = L2 within [-under, +over] x ATR(H1) of L1
(L2 slightly below L1 = a small undercut, also a double bottom). Entry at the next M15 open, stop beyond min(L1, L2) + buf.
Also prints J's trades split by (L2-L1)/ATR to see whether the double-bottom ones carry the edge.
Usage: python db_ea.py [label]"""
import sys, bisect, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import turn_ea as TE  # noqa: E402
X = TE.X; B = TE.B
A1 = B.A1
OUT = TE.OUT


def pivots(R, CL):
    P = sorted((e['available_idx'], e['kind'], e['price']) for e in R['pivot_events'] if e.get('action', 'confirm') == 'confirm')
    return P, [p[0] for p in P]


PIV = {'H1': pivots(B.R1, B.C1), 'M15': pivots(B.R15, list(X.CL15))}


def dbinfo(tf, i, s):
    """(L1, L2 or None) for the provisional turn at bar i of tf."""
    R = B.R1 if tf == 'H1' else B.R15
    P, PA = PIV[tf]; kind = 'lo' if s == 1 else 'hi'
    L2 = R['prov_bars'][i][1]
    j = bisect.bisect_right(PA, i) - 1; seen = []
    while j >= 0 and len(seen) < 3:
        if P[j][1] == kind:
            seen.append(P[j][2])
        j -= 1
    # L1 = the most extreme of the previous confirmed swings on that side, other than L2 itself
    cand = [p for p in seen if abs(p - L2) > 1e-9]
    if not cand:
        return None, L2
    L1 = min(cand) if s == 1 else max(cand)
    return L1, L2


def events(tf='M15', h4='same', under=0.3, over=0.6, db=True):
    R, CL = (B.R1, B.C1) if tf == 'H1' else (B.R15, list(X.CL15))
    ev = []
    for e in R['prov_events']:
        if e['action'] not in ('REVERSAL', 'PROV_START'):
            continue
        i = e['idx']; to = e['to']; s = 1 if to == 'up' else -1
        if R['bars'][i][0] == to:
            continue
        L1, L2 = dbinfo(tf, i, s)
        if L2 is None or not np.isfinite(L2):
            continue
        t = CL[i]; k1 = bisect.bisect_right(B.C1, t) - 1; a = A1[k1]
        d = s * (L2 - L1) / a if L1 is not None else np.nan
        if db and not (np.isfinite(d) and -under <= d <= over):
            continue
        if h4 != 'none':
            k4 = bisect.bisect_right(B.C4, t) - 1
            if k4 < 0 or B.R4['prov_bars'][k4][0] != to:
                continue
        ref = min(L1, L2) if (s == 1 and L1 is not None) else (max(L1, L2) if L1 is not None else L2)
        ev.append(dict(t=t, side=s, tag='db', ref=ref, win=1, d=d))
    return ev


GRID = dict(tf=('M15', 'H1'), h4=('same', 'none'), band=((0.3, 0.6), (0.5, 1.0), (0.3, 0.3), (1.0, 1.5)), buf=(0.3,))


def run1(c):
    ev = events(c['tf'], c['h4'], c['band'][0], c['band'][1])
    tr = X.run(ev, dict(trig='now', stop='ref', buf=c['buf'], exit='h1', act=1.0, win=1))
    key = f"{c['tf']}_{c['h4']}_u{c['band'][0]}o{c['band'][1]}"
    tr.to_csv(OUT / f'db_{key}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    def st(m):
        rr = r[m]; w = rr > 0
        return len(rr), rr.sum(), rr[w].sum() / max(1e-9, -rr[~w].sum())
    a = st((y >= 2005) & (y <= 2015)); b = st((y >= 2016) & (y <= 2026))
    bl = [r[(y >= p) & (y <= q)].sum() for p, q in TE.BL5]
    return dict(key=key, n1=a[0], R1=a[1], PF1=a[2], n2=b[0], R2=b[1], PF2=b[2], b=' '.join(f'{v:+.0f}' for v in bl))


if __name__ == '__main__':
    lab = sys.argv[1] if len(sys.argv) > 1 else 'x'
    # 1) J's trades split by how close L2 is to L1
    ev = events('M15', 'same', db=False); E = pd.DataFrame(ev)
    tr = X.run(ev, dict(trig='now', stop='ref', buf=0.3, exit='h1', act=1.0, win=1))
    tr = tr.merge(E[['t', 'side', 'd']].rename(columns={'t': 'setup_t'}), on=['setup_t', 'side'], how='left')
    tr['grp'] = pd.cut(tr.d, [-99, -0.3, 0, 0.3, 0.6, 1.0, 2.0, 99], labels=['L1を0.3超え下抜け', '下抜け0.3以内', '上0〜0.3', '上0.3〜0.6', '上0.6〜1.0', '上1〜2', '上2以上'])
    y = tr.t.dt.year
    print('== J のトレードを「2つ目の安値 − 1つ目の安値」(H1 ATR) で分けた成績（前半 / 後半）')
    for g, d_ in tr.groupby('grp', observed=True):
        yy = d_.t.dt.year
        def pf(m):
            r = d_.R[m]; w = r > 0; return f'{len(r):4d}回 {r.sum():+6.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f}'
        print(f'  {g:14s} {pf((yy <= 2015))} | {pf((yy >= 2016))}')
    C = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    with Pool(3) as p:
        rows = list(p.imap_unordered(run1, C))
    D = pd.DataFrame(rows).sort_values('PF1', ascending=False); D.to_csv(OUT / f'db_summary_{lab}.csv', index=False)
    pd.set_option('display.width', 220); print(D.round(2).to_string(index=False))
