"""Template 'turn follower' (for pairs that keep going after a turn, e.g. USDJPY; 2026-10-21).
Setup: a provisional turn on `tf` (H1 or M15) made BEFORE the major trend has turned (higher low after a down trend,
mirrored) -> enter at the next M15 open, no waiting for the lower high to break.
Stop: beyond the provisional protected swing (the higher low) + buf x ATR(H1). Exit: H1 swing trail from +act R.
Options: h4 = require the H4 provisional trend (none / same / major opposite = early H4 turn), notri, maxdev.
Split: design on 2005-2015, check 2016-2026 untouched. Usage: python turn_ea.py [label]"""
import sys, bisect, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'turn'; OUT.mkdir(exist_ok=True, parents=True)
X.add_trigger('now', lambda: {d: list(range(X.N)) for d in ('up', 'down')})
CL1 = B.C1


def events(tf='H1', h4='none', before=True):
    R, CL = (B.R1, CL1) if tf == 'H1' else (B.R15, list(X.CL15))
    ev = []
    for e in R['prov_events']:
        if e['action'] not in ('REVERSAL', 'PROV_START'):
            continue
        i = e['idx']; to = e['to']; s = 1 if to == 'up' else -1
        if before and R['bars'][i][0] == to:
            continue
        ref = R['prov_bars'][i][1]
        if ref is None or not np.isfinite(ref):
            continue
        t = CL[i]
        if h4 != 'none':
            k4 = bisect.bisect_right(B.C4, t) - 1
            if k4 < 0:
                continue
            p4 = B.R4['prov_bars'][k4][0]; m4 = B.R4['bars'][k4][0]
            if h4 == 'same' and p4 != to:
                continue
            if h4 == 'major_same' and m4 != to:
                continue
        ev.append(dict(t=t, side=s, tag=f'turn{tf}', ref=ref, win=1))
    return ev


GRID = dict(tf=('H1', 'M15'), h4=('none', 'same', 'major_same'), buf=(0.3, 0.6), act=(1.0, 1.5))
BL2 = ((2005, 2015), (2016, 2026))
BL5 = ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))


def run1(c):
    ev = events(c['tf'], c['h4'])
    cfg = dict(trig='now', stop='ref', buf=c['buf'], exit='h1', act=c['act'], win=1)
    tr = X.run(ev, cfg)
    key = f"{c['tf']}_{c['h4']}_b{c['buf']}_a{c['act']}"
    tr.to_csv(OUT / f'turn_{key}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    def st(m):
        rr = r[m]; w = rr > 0
        return len(rr), rr.sum(), rr[w].sum() / max(1e-9, -rr[~w].sum())
    h1 = st((y >= 2005) & (y <= 2015)); h2 = st((y >= 2016) & (y <= 2026))
    b = [r[(y >= a) & (y <= z)].sum() for a, z in BL5]
    return dict(key=key, **c, n1=h1[0], R1=h1[1], PF1=h1[2], n2=h2[0], R2=h2[1], PF2=h2[2], b=' '.join(f'{v:+.0f}' for v in b))


if __name__ == '__main__':
    lab = sys.argv[1] if len(sys.argv) > 1 else 'x'
    C = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    with Pool(3) as p:
        rows = list(p.imap_unordered(run1, C))
    D = pd.DataFrame(rows).sort_values('PF1', ascending=False)
    D.to_csv(OUT / f'summary_{lab}.csv', index=False)
    pd.set_option('display.width', 220)
    print(D[['key', 'n1', 'R1', 'PF1', 'n2', 'R2', 'PF2', 'b']].round(2).to_string(index=False))
