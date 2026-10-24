"""Wider stop for noisy pairs (user: GBP moves are large; stop at the M15 Dow turn). One knob only: stop buffer beyond the
M15 turn swing, x ATR(H1): 1.0 (now) / 1.5 / 2.0, for C (ea_core) and A (retest N1). First/second half."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
import step2_newea as S2  # noqa: E402
import retest_ea as RT  # noqa: E402
def pf(r): w = r > 0; return r[w].sum() / max(1e-9, -r[~w].sum())
def line(lab, t, R, risk):
    t = pd.DatetimeIndex(t); R = np.asarray(R); m = t.year >= 2005; t = t[m]; R = R[m]; y = t.year
    print(f'{lab:22s} n={len(R):4d} {R.sum():+6.1f}R PF{pf(R):.2f} 勝率{(R > 0).mean():.0%} | 前半 {R[y <= 2015].sum():+.1f}R PF{pf(R[y <= 2015]):.2f} | 後半 {R[y >= 2016].sum():+.1f}R PF{pf(R[y >= 2016]):.2f} | 損切り中央{np.median(np.asarray(risk)[m]) / 1e-4:.0f}p', flush=True)
EV = S2.cl15_events()
for b in (1.0, 1.5, 2.0):
    tr = X.run(EV, dict(trig='dow', stop='m15turn', buf=b, exit='h1', act=1.0, dside=0, maxdev=4, notri='H4'))
    line(f'C 余裕{b}ATR', tr.t, tr.R, tr.risk)
N1 = [c for c in RT.CFGS if c['name'].startswith('N1')][0]
for b in (1.0, 1.5, 2.0):
    name, tr = RT.run(dict(N1, buf=b))
    line(f'A 余裕{b}ATR', tr.t, tr.R, tr.risk)
