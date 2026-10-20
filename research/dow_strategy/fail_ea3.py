"""EA-F v3: touch-and-hold H1 SMA75 without waiting for the H1 swing to confirm.
Setup at an H1 close (buy): the bar's low came within `near` ATR of SMA75 (or poked below it) and the bar CLOSED above it;
that low is above the last confirmed H1 swing low (higher low = the push failed); trend: SMA200 rising [s200], SMA75 rising [s75].
Entry: M15 provisional turn up within `win` h. Stop below the touch low (+buf) [ref] or the M15 turn."""
import sys, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fail_ea as F  # noqa: E402
X = F.X; B = F.B; c1 = F.c1; hh = F.hh; ll = F.ll; A1 = F.A1; S75 = F.S75; S200 = F.S200
LOP = [(av, p) for av, idx, kind, p in F.PV if kind == 'lo']; HIP = [(av, p) for av, idx, kind, p in F.PV if kind == 'hi']
LOA = [a for a, _ in LOP]; HIA = [a for a, _ in HIP]


def events(near=0.3, s200=True, s75=True, hl=True, win=12, gap=6):
    ev = []; lastk = {1: -999, -1: -999}
    for k in range(250, len(c1)):
        for s in (1, -1):
            ext = ll[k] if s == 1 else hh[k]
            if not (s * (c1[k] - S75[k]) > 0 and s * (ext - S75[k]) <= near * A1[k]):
                continue
            if s200 and not s * (S200[k] - S200[k - 30]) > 0:
                continue
            if s75 and not s * (S75[k] - S75[k - 10]) > 0:
                continue
            if hl:
                A_, P_ = (LOA, LOP) if s == 1 else (HIA, HIP)
                j = bisect.bisect_right(A_, k) - 1
                if j < 0 or s * (ext - P_[j][1]) <= 0:
                    continue
            if k - lastk[s] < gap:
                continue
            lastk[s] = k
            seg = ll[k - 3:k + 1].min() if s == 1 else hh[k - 3:k + 1].max()
            ev.append(dict(t=B.C1[k], side=s, tag='touch75', ref=seg, win=win))
    return ev


BASE = dict(near=0.3, s200=True, s75=True, hl=True, win=12, stop='ref', buf=0.3)
V = {'base': {}, 'near0': dict(near=0.0), 'near06': dict(near=0.6), 'no75': dict(s75=False), 'no200': dict(s200=False),
     'nohl': dict(hl=False), 'win6': dict(win=6), 'win24': dict(win=24), 'stop_turn': dict(stop='m15turn', buf=1.0),
     'notri': dict(notri='H4'), 'dside': dict(dside=0)}


def run1(k):
    c = dict(BASE); c.update(V[k])
    ev = events(c['near'], c['s200'], c['s75'], c['hl'], c['win'])
    cfg = dict(trig='dow', stop=c['stop'], buf=c['buf'], exit='h1', act=1.0, notri=c.get('notri'), dside=c.get('dside'))
    tr = X.run(ev, cfg); tr.to_csv(F.OUT / f'touch75_{k}.csv', index=False)
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
