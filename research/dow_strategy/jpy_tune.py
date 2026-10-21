"""USDJPY tuning backed by the character ruler (2026-10-21). Only knobs the ruler supports:
  session 0-10h (turns follow through mainly then), H1 major trend same (follow-through strongest with H1 aligned),
  exit width (trends persist on JPY -> later trail activation / H1 trail kept).
Applied to J2 and to C (the correction-line break, same Dow-turn entry). Chosen on 2005-2015, checked on 2016-2026."""
import sys, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import turn_tune as TT  # noqa: E402
import step2_newea as S2  # noqa: E402
X = TT.X; TE = TT.TE; B = TT.B
J2EV = TT.h1filter(TT.h1filter(TT.BASEEV, 'h1major'), 'hour0_10')
CEV = S2.cl15_events()
def cfilter(mode):
    ev = CEV
    if 'h1' in mode:
        ev = [e for e in ev if B.R1['bars'][bisect.bisect_right(B.C1, e['t']) - 1][0] == ('up' if e['side'] == 1 else 'down')]
    if 'sess' in mode:
        ev = [e for e in ev if (e['t'] - pd.Timedelta(minutes=15)).hour < 10]
    return ev
C0 = dict(trig='dow', stop='m15turn', buf=1.0, exit='h1', act=1.0, dside=0, maxdev=4, notri='H4')
V = {'J2': (J2EV, TT.BASE), 'J2_act1.5': (J2EV, dict(TT.BASE, act=1.5)), 'J2_act2': (J2EV, dict(TT.BASE, act=2.0)),
     'J2_buf0.6': (J2EV, dict(TT.BASE, buf=0.6)), 'J2_hyb': (J2EV, dict(TT.BASE, exit='hyb', sw=2.0)),
     'C': (CEV, C0), 'C_h1': (cfilter('h1'), C0), 'C_sess': (cfilter('sess'), C0), 'C_h1_sess': (cfilter('h1sess'), C0),
     'C_act1.5': (CEV, dict(C0, act=1.5)), 'C_nodside': (CEV, dict(C0, dside=None))}
def run1(k):
    ev, cfg = V[k]; tr = X.run(ev, cfg); tr.to_csv(TE.OUT / f'jpy_{k}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    def st(m):
        rr = r[m]; w = rr > 0; eq = rr.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min() if len(eq) else 0
        return len(rr), rr.sum(), rr[w].sum() / max(1e-9, -rr[~w].sum()), dd
    a = st(y <= 2015); b = st(y >= 2016); bl = [r[(y >= p) & (y <= q)].sum() for p, q in TE.BL5]
    return dict(key=k, n1=a[0], R1=a[1], PF1=a[2], DD1=a[3], n2=b[0], R2=b[1], PF2=b[2], DD2=b[3], b=' '.join(f'{v:+.0f}' for v in bl))
if __name__ == '__main__':
    with Pool(3) as p:
        rows = list(p.imap_unordered(run1, list(V)))
    D = pd.DataFrame(rows); D.to_csv(TE.OUT / f'jpy_tune_{sys.argv[1] if len(sys.argv) > 1 else "x"}.csv', index=False)
    pd.set_option('display.width', 220); print(D.round(2).to_string(index=False))
