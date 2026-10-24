"""EA-F v2: failed push AT the H1 SMA75 (user: 'H1 75 is where I always watch for the bounce').
Setup when a new H1 swing low L2 is confirmed (buy; sell mirrored):
  - L2 is a higher low than the previous H1 low (the push down failed)
  - L2 is within `near` x ATR(H1) of H1 SMA75 (tested the 75 and held)
  - price has closed back above H1 SMA75
  - trend filter: H1 SMA200 rising over 30 bars [s200] and/or H4 provisional trend up [h4p]
Entry: M15 provisional turn up within `win` h. Stop beyond L2 (+buf ATR) or the M15 turn. Exit H1 swing trail from +1R."""
import sys, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fail_ea as F  # noqa: E402
X = F.X; B = F.B; c1 = F.c1; A1 = F.A1; S75 = F.S75; S200 = F.S200
PV = F.PV


def events(near=0.7, s200=True, h4p=True, hl=True, win=24):
    ev = []; last = {'lo': None, 'hi': None}
    for av, idx, kind, price in PV:
        prev = last[kind]; last[kind] = (idx, price)
        if prev is None:
            continue
        s = 1 if kind == 'lo' else -1; k = av
        if hl and s * (price - prev[1]) <= 0:
            continue
        if abs(price - S75[k]) > near * A1[k] or not s * (c1[k] - S75[k]) > 0:
            continue
        if s200 and not s * (S200[k] - S200[k - 30]) > 0:
            continue
        if h4p:
            k4 = bisect.bisect_right(B.C4, B.C1[k]) - 1
            if B.R4['prov_bars'][k4][0] != ('up' if s == 1 else 'down'):
                continue
        ev.append(dict(t=B.C1[k], side=s, tag='fail75', ref=price, win=win))
    return ev


BASE = dict(near=0.7, s200=True, h4p=True, hl=True, win=24, stop='ref', buf=0.3)
V = {'base': {}, 'near05': dict(near=0.5), 'near10': dict(near=1.0), 'no200': dict(s200=False), 'noh4p': dict(h4p=False),
     'nohl': dict(hl=False), 'win12': dict(win=12), 'win48': dict(win=48), 'stop_turn': dict(stop='m15turn', buf=1.0),
     'buf06': dict(buf=0.6), 'notri': dict(notri='H4'), 'md3': dict(maxdev=3)}


def run1(k):
    c = dict(BASE); c.update(V[k])
    ev = events(c['near'], c['s200'], c['h4p'], c['hl'], c['win'])
    cfg = dict(trig='dow', stop=c['stop'], buf=c['buf'], exit='h1', act=1.0, notri=c.get('notri'), maxdev=c.get('maxdev'))
    tr = X.run(ev, cfg); tr.to_csv(F.OUT / f'fail75_{k}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    b = [r[(y >= a) & (y <= z)].sum() for a, z in ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]
    w = r > 0; eq = r.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(); yy = tr.groupby(y).R.sum()
    P = pd.read_csv(B.HERE / 'results' / 'user_points_shape.csv', parse_dates=['time'])
    E = pd.DataFrame(ev); cov = np.mean([((E.side == p.side) & ((E.t - p.time) <= pd.Timedelta(hours=12)) & ((p.time - E.t) <= pd.Timedelta(hours=48))).any() for p in P.itertuples()])
    return f"{k:9s} setup{len(ev):5d} 点カバー{cov:4.0%} n={len(r):4d} {r.sum():+6.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} 勝率{w.mean():.0%} DD{dd:6.1f} 負け年{(yy < 0).sum()}/{len(yy)} SL{tr.risk.median() / 1e-4:3.0f}p | " + ' '.join(f'{v:+.1f}' for v in b) + ('  ★' if min(b) > 0 else '')


if __name__ == '__main__':
    with Pool(3) as p:
        for s in p.imap_unordered(run1, list(V)):
            print(s, flush=True)
