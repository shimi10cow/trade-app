"""Exit ideas from the feedback, checked on the actual trade paths (2026-10-22). Run inside a pair workspace.
(a) break-even: once the best unrealised gain reaches X R, the stop moves to entry + 0.1R (exit there if hit before the
    original exit). (b) M15 turn exit: once the gain reached X R, exit at the next M15 open after an M15 provisional Dow
    turn against the trade (if that comes before the original exit). Original exits are kept otherwise.
Usage: python exit_posthoc.py <results dir> <out csv> <cost pips> code:file ..."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
RD = Path(sys.argv[1]); OUT = sys.argv[2]; COST = float(sys.argv[3]) * 1e-4
T15 = np.array(B.T15, dtype='datetime64[ns]'); o, h, l = B.o, B.h, B.l
turn = {1: set(), -1: set()}
for e in B.R15['prov_events']:
    if e['action'] in ('REVERSAL', 'PROV_START'):
        turn[1 if e['to'] == 'up' else -1].add(e['idx'])
rows = []
for spec in sys.argv[4:]:
    code, f = spec.split(':', 1); d = pd.read_csv(RD / f)
    if 'Rc' in d: t, xt, R, sl0 = pd.to_datetime(d.time), pd.to_datetime(d.ExitTime), d.Rc.to_numpy(), d.initial_sl.to_numpy()
    else: t, xt, R, sl0 = pd.to_datetime(d.t), pd.to_datetime(d.exit_t), d.R.to_numpy(), (d.entry - d.side * d.risk).to_numpy()
    for k, (ti, xi, s, e, rk) in enumerate(zip(t, xt, d.side, d.entry, d.risk)):
        if ti.year < 2005 or pd.isna(xi): continue
        i0 = np.searchsorted(T15, np.datetime64(ti)); i1 = np.searchsorted(T15, np.datetime64(xi))
        best = 0.0; res = dict(ea=code, t=ti, year=ti.year, side=s, R=R[k], risk=rk)
        for X in (1.0, 1.5, 2.0):
            res[f'be{X}'] = R[k]; res[f'm15_{X}'] = R[k]
        be_on = {X: False for X in (1.0, 1.5, 2.0)}; m15_on = {X: False for X in (1.0, 1.5, 2.0)}
        done_be = {X: False for X in (1.0, 1.5, 2.0)}; done_m = {X: False for X in (1.0, 1.5, 2.0)}
        for i in range(i0, min(i1, len(h))):
            for X in (1.0, 1.5, 2.0):          # stops first (armed from earlier bars only)
                if be_on[X] and not done_be[X]:
                    lvl = e + s * 0.1 * rk
                    if (l[i] <= lvl) if s == 1 else (h[i] >= lvl):
                        res[f'be{X}'] = 0.1 - COST / rk; done_be[X] = True
            fav = ((h[i] - e) if s == 1 else (e - l[i])) / rk; best = max(best, fav)
            for X in (1.0, 1.5, 2.0):
                if best >= X: be_on[X] = True; m15_on[X] = True
                if m15_on[X] and not done_m[X] and i in turn[-s] and i + 1 < len(o):
                    res[f'm15_{X}'] = (o[i + 1] - e) * s / rk - COST / rk; done_m[X] = True
        rows.append(res)
pd.DataFrame(rows).to_csv(OUT, index=False); print(len(rows), 'trades ->', OUT)
