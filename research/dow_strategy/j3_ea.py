"""J3: follow an H1 major reversal (ruler: on USDJPY the move after an H1 major turn is +0.19 ATR/96 bars, both halves).
Entry at the next M15 open after the H1 bar that reversed; stop at the H1 protected level (h1prot) or the last H1 swing;
H1 swing trail. Options: H4 provisional same, session 0-10h. First half chooses, second half checks."""
import sys, bisect, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import turn_ea as TE  # noqa: E402
X = TE.X; B = TE.B
def events(h4=True, sess=False):
    ev = []
    for e in B.R1['events']:
        if e.get('machine') != 'major' or e['action'] != 'REVERSAL':
            continue
        t = B.C1[e['idx']]; to = e['to']; s = 1 if to == 'up' else -1
        if h4:
            k4 = bisect.bisect_right(B.C4, t) - 1
            if k4 < 0 or B.R4['prov_bars'][k4][0] != to: continue
        if sess and not (t - pd.Timedelta(hours=1)).hour < 10: continue
        ev.append(dict(t=t, side=s, tag='j3', win=1))
    return ev
GRID = dict(h4=(True, False), sess=(False, True), stop=('h1prot', 'h1swing'), buf=(0.3,))
def run1(c):
    tr = X.run(events(c['h4'], c['sess']), dict(trig='now', stop=c['stop'], buf=c['buf'], exit='h1', act=1.0, win=1))
    key = f"h4{int(c['h4'])}_s{int(c['sess'])}_{c['stop']}"; tr.to_csv(TE.OUT / f'j3_{key}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    def st(m):
        rr = r[m]; w = rr > 0; return len(rr), rr.sum(), rr[w].sum() / max(1e-9, -rr[~w].sum())
    a = st(y <= 2015); b = st(y >= 2016); bl = [r[(y >= p) & (y <= q)].sum() for p, q in TE.BL5]
    return dict(key=key, n1=a[0], R1=a[1], PF1=a[2], n2=b[0], R2=b[1], PF2=b[2], b=' '.join(f'{v:+.0f}' for v in bl))
if __name__ == '__main__':
    C = [dict(zip(GRID, v)) for v in itertools.product(*GRID.values())]
    with Pool(3) as p:
        rows = list(p.imap_unordered(run1, C))
    D = pd.DataFrame(rows).sort_values('PF1', ascending=False); D.to_csv(TE.OUT / f'j3_summary_{sys.argv[1] if len(sys.argv) > 1 else "x"}.csv', index=False)
    pd.set_option('display.width', 200); print(D.round(2).to_string(index=False))
