"""EA-S 'head & shoulders denied' (user 2026-10-20; buy shown = a top that failed; sell mirrored = inverse H&S that failed).
H1 confirmed swings: left shoulder high LS, head high HD > LS, right shoulder high RS < HD (the place sellers expect to sell),
neckline lows NL1 (LS-HD) and NL2 (HD-RS). After RS, the next H1 swing low L3 does NOT break the neckline
(L3 > min(NL1, NL2) - tol x ATR) = the H&S is denied. Setup known when L3 is confirmed.
Entry: M15 provisional turn up within `win` h [trig=turn], or an H1 close above RS [trig=rs].
Stop below L3 (+buf ATR). Exit H1 swing trail from +1R."""
import sys, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fail_ea as F  # noqa: E402
X = F.X; B = F.B; c1 = F.c1; A1 = F.A1; S75 = F.S75; S200 = F.S200


def events(tol=0.0, win=24, rsbreak=False, shoulder=True, trend=None):
    ev = []; seq = []
    for av, idx, kind, p in F.PV:
        seq.append((av, idx, kind, p))
        if len(seq) < 6:
            continue
        a, b, c, d, e, f = seq[-6:]
        for s, top, bot in ((1, 'hi', 'lo'), (-1, 'lo', 'hi')):
            # buy: LS(hi) NL1(lo) HD(hi) NL2(lo) RS(hi) L3(lo)
            if [x[2] for x in (a, b, c, d, e, f)] != [top, bot, top, bot, top, bot]:
                continue
            LS, NL1, HD, NL2, RS, L3 = (x[3] for x in (a, b, c, d, e, f))
            if not (s * (HD - LS) > 0 and s * (HD - RS) > 0):
                continue                                         # a head above both shoulders
            if shoulder and not s * (RS - max(NL1, NL2) if s == 1 else RS - min(NL1, NL2)) > 0:
                continue
            k = f[0]; neck = min(NL1, NL2) if s == 1 else max(NL1, NL2)
            if s * (L3 - neck) <= -tol * A1[k]:
                continue                                         # neckline broken: H&S worked, no denial
            if trend == 's200' and not s * (S200[k] - S200[k - 30]) > 0:
                continue
            if trend == 'ma75' and not s * (c1[k] - S75[k]) > 0:
                continue
            ev.append(dict(t=B.C1[k], side=s, tag='hsdeny', ref=L3, win=win, rs=RS))
    if rsbreak:                                                  # wait for an H1 close beyond RS, then the M15 turn
        out = []
        for e_ in ev:
            k0 = bisect.bisect_right(B.C1, e_['t']) - 1
            for k in range(k0 + 1, min(k0 + 72, len(c1))):
                if e_['side'] * (c1[k] - e_['ref']) < 0:
                    break
                if e_['side'] * (c1[k] - e_['rs']) > 0:
                    out.append(dict(e_, t=B.C1[k])); break
        ev = out
    return ev


BASE = dict(tol=0.0, win=24, rsbreak=False, shoulder=True, trend=None, stop='ref', buf=0.3)
V = {'base': {}, 'tol03': dict(tol=0.3), 'win12': dict(win=12), 'win48': dict(win=48), 'rsbreak': dict(rsbreak=True),
     'noshoulder': dict(shoulder=False), 's200': dict(trend='s200'), 'ma75': dict(trend='ma75'),
     'stop_turn': dict(stop='m15turn', buf=1.0), 'notri': dict(notri='H4'), 'dside': dict(dside=0)}


def run1(k):
    c = dict(BASE); c.update(V[k])
    ev = events(c['tol'], c['win'], c['rsbreak'], c['shoulder'], c['trend'])
    cfg = dict(trig='dow', stop=c['stop'], buf=c['buf'], exit='h1', act=1.0, notri=c.get('notri'), dside=c.get('dside'))
    tr = X.run(ev, cfg); tr.to_csv(F.OUT / f'hsdeny_{k}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    b = [r[(y >= a) & (y <= z)].sum() for a, z in ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]
    w = r > 0; eq = r.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(); yy = tr.groupby(y).R.sum()
    P = pd.read_csv(B.HERE / 'results' / 'user_points_shape.csv', parse_dates=['time'])
    T = pd.DataFrame(dict(t=tr.t, side=tr.side))
    cov = np.mean([((T.side == p.side) & ((T.t - p.time).abs() <= pd.Timedelta(hours=12))).any() for p in P.itertuples()])
    return f"{k:10s} setup{len(ev):5d} 点にEAが入った{cov:4.0%} n={len(r):4d} {r.sum():+6.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} 勝率{w.mean():.0%} DD{dd:6.1f} 負け年{(yy < 0).sum()}/{len(yy)} SL{tr.risk.median() / 1e-4:3.0f}p | " + ' '.join(f'{v:+.1f}' for v in b) + ('  ★' if min(b) > 0 else '')


if __name__ == '__main__':
    with Pool(2) as p:
        for s in p.imap_unordered(run1, list(V)):
            print(s, flush=True)
