"""EA-K 'box break -> retest holds -> higher-low entry' (user picture 2026-10-20; buy shown, sell mirrored).
  1. Line: an H1 resistance = >= `ntouch` confirmed H1 swing highs within tol x ATR(H1) of each other during the last
     `look` H1 bars, with no H1 close above (line + tol) in between (a box top / double top that held).
  2. Break: an H1 close above line + 0.1 ATR.
  3. Retest: within `rwin` H1 bars after the break, an H1 low comes back to within `near` ATR of the line,
     without an H1 close below line - `fail` ATR (it cannot fall back into the box).
  4. Entry: after the retest, the M15 provisional turn up (the higher low above the line) within `win` h.
  Stop below the retest low (+buf ATR) [ref] or the M15 turn. Exit: H1 swing trail from +1R. Causal."""
import sys, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fail_ea as F  # noqa: E402
X = F.X; B = F.B; c1 = F.c1; hh = F.hh; ll = F.ll; A1 = F.A1; S75 = F.S75; S200 = F.S200
PV = F.PV
N1 = len(c1)


def lines(look=120, ntouch=2, tol=0.3):
    """For each H1 bar k (as of its close): list of (side, level) lines currently valid (not yet broken)."""
    out = []                                            # (k_break, side, level)
    piv = {'hi': [], 'lo': []}; j = 0
    active = {}                                         # (side, level) -> formed k
    for k in range(N1):
        while j < len(PV) and PV[j][0] <= k:
            av, idx, kind, p = PV[j]; piv[kind].append((idx, p)); j += 1
            s = 1 if kind == 'hi' else -1                # resistance (hi) -> buy on break up
            rec = [(i, q) for i, q in piv[kind] if i >= k - look]
            near = [(i, q) for i, q in rec if abs(q - p) <= tol * A1[k]]
            if len(near) >= ntouch:
                lvl = max(q for _, q in near) if s == 1 else min(q for _, q in near)
                i0 = min(i for i, _ in near)
                cl = c1[i0:k + 1]
                if (s == 1 and cl.max() <= lvl + tol * A1[k]) or (s == -1 and cl.min() >= lvl - tol * A1[k]):
                    active[(s, round(lvl, 5))] = k
        for (s, lvl), kf in list(active.items()):
            if k - kf > look:
                del active[(s, lvl)]; continue
            if s * (c1[k] - lvl) > 0.1 * A1[k]:
                out.append((k, s, lvl)); del active[(s, lvl)]
    return out


def events(look=120, ntouch=2, tol=0.3, rwin=48, near=0.3, fail=0.3, win=12, trend=None):
    ev = []
    for kb, s, lvl in lines(look, ntouch, tol):
        for k in range(kb + 1, min(kb + rwin, N1)):
            if s * (c1[k] - lvl) < -fail * A1[k]:
                break                                    # fell back into the box: dead
            ext = ll[k] if s == 1 else hh[k]
            if s * (ext - lvl) <= near * A1[k]:
                if trend == 's200' and not s * (S200[k] - S200[k - 30]) > 0:
                    break
                if trend == 'ma75' and not s * (c1[k] - S75[k]) > 0:
                    break
                lo = ll[kb + 1:k + 1].min() if s == 1 else hh[kb + 1:k + 1].max()
                ev.append(dict(t=B.C1[k], side=s, tag='flip', ref=lo, win=win))
                break
    return ev


BASE = dict(look=120, ntouch=2, tol=0.3, rwin=48, near=0.3, fail=0.3, win=12, trend=None, stop='ref', buf=0.3)
V = {'base': {}, 'touch3': dict(ntouch=3), 'look240': dict(look=240), 'tol02': dict(tol=0.2), 'rwin96': dict(rwin=96),
     'near05': dict(near=0.5), 'fail05': dict(fail=0.5), 'win24': dict(win=24), 's200': dict(trend='s200'), 'ma75': dict(trend='ma75'),
     'stop_turn': dict(stop='m15turn', buf=1.0), 'notri': dict(notri='H4'), 'dside': dict(dside=0)}


def run1(k):
    c = dict(BASE); c.update(V[k])
    ev = events(c['look'], c['ntouch'], c['tol'], c['rwin'], c['near'], c['fail'], c['win'], c['trend'])
    cfg = dict(trig='dow', stop=c['stop'], buf=c['buf'], exit='h1', act=1.0, notri=c.get('notri'), dside=c.get('dside'))
    tr = X.run(ev, cfg); tr.to_csv(F.OUT / f'flip_{k}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    b = [r[(y >= a) & (y <= z)].sum() for a, z in ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]
    w = r > 0; eq = r.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(); yy = tr.groupby(y).R.sum()
    P = pd.read_csv(B.HERE / 'results' / 'user_points_shape.csv', parse_dates=['time'])
    T = pd.DataFrame(dict(t=tr.t, side=tr.side))
    cov = np.mean([((T.side == p.side) & ((T.t - p.time).abs() <= pd.Timedelta(hours=12))).any() for p in P.itertuples()])
    return f"{k:9s} setup{len(ev):5d} 点にEAが入った{cov:4.0%} n={len(r):4d} {r.sum():+6.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} 勝率{w.mean():.0%} DD{dd:6.1f} 負け年{(yy < 0).sum()}/{len(yy)} SL{tr.risk.median() / 1e-4:3.0f}p | " + ' '.join(f'{v:+.1f}' for v in b) + ('  ★' if min(b) > 0 else '')


if __name__ == '__main__':
    with Pool(3) as p:
        for s in p.imap_unordered(run1, list(V)):
            print(s, flush=True)
