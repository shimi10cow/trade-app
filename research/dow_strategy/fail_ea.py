"""EA-F 'failed to fall / failed to rise' (user idea 2026-10-20; buy side, sell mirrored).
Setup (known when the new H1 swing low is confirmed):
  - the market had been falling into the previous H1 low L1: L1 is the lowest low of the `look` H1 bars before it
  - the new H1 low L2 is HIGHER than L1 (the fall failed; inverse H&S / denied H&S)
  - H1 SMA75 has started to turn up (slope over the last 10 H1 bars > 0)            [ma]
  - price above H1 SMA75 (and SMA200)                                               [pos]
Entry: the M15 provisional turn up within `win` hours (no waiting for the neckline). Stop beyond L2 (+buf x ATR H1) or the M15 turn.
Exit: H1 swing trail from +1R (same as the other EAs). Cost 1.2 pip. Causal."""
import sys, bisect, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'step2'
h1 = B.h1; c1 = h1.c.to_numpy(float); hh = h1.h.to_numpy(float); ll = h1.l.to_numpy(float); A1 = B.A1
S75 = pd.Series(c1).rolling(75).mean().to_numpy(); S200 = pd.Series(c1).rolling(200).mean().to_numpy()
PV = sorted((e['available_idx'], e['idx'], e['kind'], e['price']) for e in B.R1['pivot_events'] if e.get('action', 'confirm') == 'confirm')


def events(look=120, ma=True, pos='75', hlmin=0.0, win=24):
    ev = []; last = {'lo': None, 'hi': None}
    for av, idx, kind, price in PV:
        prev = last[kind]; last[kind] = (idx, price)
        if prev is None:
            continue
        s = 1 if kind == 'lo' else -1
        i1, p1 = prev
        seg = ll[max(0, i1 - look):i1] if s == 1 else hh[max(0, i1 - look):i1]
        if not len(seg) or (s == 1 and p1 > seg.min()) or (s == -1 and p1 < seg.max()):
            continue                                                    # L1 must end a decline
        k = av
        if s * (price - p1) <= hlmin * A1[k]:
            continue                                                    # no higher low -> not a failure
        if ma and not (s * (S75[k] - S75[k - 10]) > 0):
            continue
        if pos in ('75', '75_200') and not (s * (c1[k] - S75[k]) > 0):
            continue
        if pos == '75_200' and not (s * (c1[k] - S200[k]) > 0):
            continue
        ev.append(dict(t=B.C1[k], side=s, tag='fail', ref=price, win=win))
    return ev


BASE = dict(look=120, ma=True, pos='75', hlmin=0.0, win=24, stop='ref', buf=0.3)
V = {'base': {}, 'look240': dict(look=240), 'look60': dict(look=60), 'noma': dict(ma=False), 'pos_none': dict(pos='none'),
     'pos_200': dict(pos='75_200'), 'hl02': dict(hlmin=0.2), 'win12': dict(win=12), 'win48': dict(win=48),
     'stop_turn': dict(stop='m15turn', buf=1.0), 'buf06': dict(buf=0.6), 'dside': dict(dside=0), 'notri': dict(notri='H4')}


def run1(k):
    c = dict(BASE); c.update(V[k])
    ev = events(c['look'], c['ma'], c['pos'], c['hlmin'], c['win'])
    cfg = dict(trig='dow', stop=c['stop'], buf=c['buf'], exit='h1', act=1.0, dside=c.get('dside'), notri=c.get('notri'))
    tr = X.run(ev, cfg); tr.to_csv(OUT / f'fail_{k}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    b = [r[(y >= a) & (y <= z)].sum() for a, z in ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]
    w = r > 0; eq = r.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    yy = tr.groupby(y).R.sum()
    return f"{k:9s} setup{len(ev):5d} n={len(r):4d} {r.sum():+6.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} 勝率{w.mean():.0%} DD{dd:6.1f} 負け年{(yy < 0).sum()}/{len(yy)} SL{tr.risk.median() / 1e-4:3.0f}p | " + ' '.join(f'{v:+.1f}' for v in b) + ('  ★' if min(b) > 0 else '')


if __name__ == '__main__':
    with Pool(3) as p:
        for s in p.imap_unordered(run1, list(V)):
            print(s, flush=True)
