"""J combos (first-half choice): H1 major same + session + maxdev."""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import turn_tune as TT  # noqa: E402
X = TT.X; TE = TT.TE
def ev_for(fs):
    ev = TT.BASEEV
    for f in fs:
        ev = TT.h1filter(ev, f)
    return ev
V = {'h1major': (['h1major'], {}), 'h1major+hour0_10': (['h1major', 'hour0_10'], {}), 'h1major+maxdev4': (['h1major'], dict(maxdev=4)),
     'h1major+hour0_10+maxdev4': (['h1major', 'hour0_10'], dict(maxdev=4)), 'h1major+hour0_12': (['h1major', 'hour0_12'], {}),
     'h1major+hour0_8': (['h1major', 'hour0_8'], {}), 'h1notagainst+hour0_10': (['h1notagainst', 'hour0_10'], {}),
     'hour0_10+maxdev4': (['hour0_10'], dict(maxdev=4)), 'h1major+notri': (['h1major'], dict(notri='H4'))}
def run1(k):
    fs, cfg = V[k]; tr = X.run(ev_for(fs), dict(TT.BASE, **cfg)); tr.to_csv(TE.OUT / f'jt2_{k}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    def st(m):
        rr = r[m]; w = rr > 0; eq = rr.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min() if len(eq) else 0
        return len(rr), rr.sum(), rr[w].sum() / max(1e-9, -rr[~w].sum()), dd
    a = st(y <= 2015); b = st(y >= 2016); bl = [r[(y >= p) & (y <= q)].sum() for p, q in TE.BL5]
    return dict(key=k, n1=a[0], R1=a[1], PF1=a[2], DD1=a[3], n2=b[0], R2=b[1], PF2=b[2], DD2=b[3], b=' '.join(f'{v:+.0f}' for v in bl))
if __name__ == '__main__':
    with Pool(3) as p:
        rows = list(p.imap_unordered(run1, list(V)))
    D = pd.DataFrame(rows).sort_values('PF1', ascending=False); D.to_csv(TE.OUT / 'jt2_summary.csv', index=False)
    pd.set_option('display.width', 220); print(D.round(2).to_string(index=False))
