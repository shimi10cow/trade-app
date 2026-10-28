"""Right shoulder (DS), ported from research/dow_strategy/ds_ea.py (2026-10-24).

After an H1 (or H4) major Dow reversal, wait for a rally of at least 38% of the left-shoulder-to-neck range, then enter on
the first M15 provisional turn back (cancelled if the left shoulder is exceeded or after 5 days).
Adopted versions (INSTRUMENT_PROFILES.md): H1, pullback depth >= 4 ATR(H4)
  JP225 : stop beyond the left shoulder, 2R target, both sides
  US500 : stop beyond the left shoulder, 2R target, buys only
  XAUUSD: stop beyond the right shoulder, H1 trail from +1R, buys only
Width (2026-10-28, RESEARCH_LOG §109, JP225 / XAUUSD only): adopted setups also need >= MIN_LN_HOURS from the left shoulder (the extreme bar of
the H1 run that turned) to the neck (the deepest M15 bar before the rally). Thin shapes lost on JP225 / gold in both halves.
The setups themselves (and their tags) are unchanged; the width is carried as e['ln_h'] and applied in run_adopted.
"""
import bisect

import numpy as np
import pandas as pd

from .. import engine as E
from ..core import Frames
from env_recognition.pivots import atr

ADOPTED = {
    'JP225': dict(stop='left', exit='tp2', side=None, ln=True),
    'US500': dict(stop='left', exit='tp2', side=1, ln=False),         # width rule: no gain on US500 (§109), left out
    'XAUUSD': dict(stop='shoulder', exit='h1', side=1, ln=True),
}
MIN_DEPTH = 4.0
MIN_LN_HOURS = 24.0


def _events(F: Frames, tf):
    df, R, close = (F.h4, F.R4, F.C4) if tf == 'H4' else (F.h1, F.R1, F.C1)
    df = df.reset_index(drop=True); hi, lo = df.h.to_numpy(float), df.l.to_numpy(float); close = pd.DatetimeIndex(close)
    A4 = np.asarray(atr(F.h4.reset_index(drop=True)), float); C4 = pd.DatetimeIndex(F.C4)
    H4P = [(e['idx'], e['available_idx'], e['kind'], e['price']) for e in F.R4['pivot_events']]
    tr = [b[0] for b in R['bars']]; out = []
    k0 = 0
    for k in range(1, len(df)):
        if tr[k] != tr[k - 1]:
            prev, start = tr[k - 1], k0; k0 = k
            if not ((prev == 'up' and tr[k] == 'down') or (prev == 'down' and tr[k] == 'up')):
                continue
            s = -1 if prev == 'up' else 1
            Hx = hi[start:k + 1].max() if s == -1 else lo[start:k + 1].min()
            jx = start + int(np.argmax(hi[start:k + 1]) if s == -1 else np.argmin(lo[start:k + 1]))
            te = close[k]; k4 = C4.searchsorted(te, 'right') - 1; a4 = A4[k4] if k4 >= 0 and np.isfinite(A4[k4]) else np.nan
            ks = C4.searchsorted(close[start], 'right') - 1
            kind = 'hi' if s == -1 else 'lo'
            res = int(any(kd == kind and ks - 500 <= ix <= ks - 20 and av <= ks and abs(p - Hx) <= 0.5 * a4 for ix, av, kd, p in H4P))
            out.append(dict(te=te, side=s, H=Hx, a4=a4, res=res, t_left=pd.Timestamp(df.t.iat[jx])))
    return out


def setups(F: Frames, tf='H1'):
    CL15 = F.CL15; Mh, Ml, Mc = F.h, F.l, F.c
    TURN = {d: sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d) for d in ('up', 'down')}
    ev = []
    for e in _events(F, tf):
        s, Hx = e['side'], e['H']; i0 = CL15.searchsorted(e['te']); iend = min(CL15.searchsorted(e['te'] + pd.Timedelta('120h')), len(Mc))
        Lx = None; rally = None; ineck = None
        for i in range(i0, iend):
            if (Mh[i] > Hx) if s == -1 else (Ml[i] < Hx):
                break
            if rally is None:
                newL = min(Lx, Ml[i]) if (Lx is not None and s == -1) else (max(Lx, Mh[i]) if Lx is not None else (Ml[i] if s == -1 else Mh[i]))
                if Lx is None or newL != Lx:
                    ineck = i                                     # the bar that made the neck (deepest point so far)
                Lx = newL
                rng = abs(Hx - Lx)
                if rng > 0 and ((Mh[i] - Lx) if s == -1 else (Lx - Ml[i])) >= 0.38 * rng:
                    rally = i
                continue
            lst = TURN['down' if s == -1 else 'up']
            k = bisect.bisect_left(lst, rally)
            if k < len(lst) and lst[k] < iend:
                j = lst[k]
                seg = Mh[i0:j + 1] if s == -1 else Ml[i0:j + 1]
                if (seg.max() > Hx) if s == -1 else (seg.min() < Hx):
                    break
                sh = Mh[rally:j + 1].max() if s == -1 else Ml[rally:j + 1].min()
                retr = abs(sh - Lx) / rng
                tag = f"{tf}|{retr:.2f}|{rng / e['a4']:.2f}|{e['res']}|{(CL15[j] - e['te']) / pd.Timedelta('1h'):.0f}"
                ln_h = (pd.Timestamp(F.T15.iloc[ineck]) - e['t_left']) / pd.Timedelta('1h')
                ev.append(dict(t=CL15[j], side=s, ref_sh=sh, ref_H=Hx, neck=Lx, win=0.3, tag=tag, ln_h=ln_h))
            break
    return ev


def cfg_for(stop, ex):
    cfg = dict(trig='all', stop='ref', buf=0.3, win=0.3, one_per_side=True)
    base, _, tm = ex.partition('-t')
    if base == 'h1': cfg.update(exit='h1', act=1.0)
    elif base == 'neck': cfg.update(exit='h1', act=99, tp_px=True, tp=3.0)
    elif base.startswith('m15a'): cfg.update(exit='m15', act=float(base[4:]))
    elif base.startswith('hyb'): cfg.update(exit='hyb', act=1.0, sw=float(base[3:]))
    else: cfg.update(exit='h1', act=99, tp=2.0)
    if tm: cfg.update(tmax=float(tm), tmfe=0.5)
    return cfg


def run_variant(F: Frames, tf, stop, ex, entry_bar=True, events=None):
    """Research-equivalent run of one DS variant (all setups, no depth / side filter)."""
    evs = setups(F, tf) if events is None else events
    evs = [dict(e, ref=e['ref_sh'] if stop == 'shoulder' else e['ref_H'], tp_px=e['neck']) for e in evs]
    return E.run(F, evs, cfg_for(stop, ex), entry_bar=entry_bar)


def adopted_filter(e, side, ln_h=None):
    depth = float(e['tag'].split('|')[2])
    return depth >= MIN_DEPTH and (side is None or e['side'] == side) and (ln_h is None or ln_h >= MIN_LN_HOURS)


def run_adopted(F: Frames, sym, entry_bar=True):
    """The adopted DS for `sym`, as validated: run with ALL setups (so a filtered-out setup can still occupy its side, exactly
    like the research run), then keep only trades / open positions / pending entries that pass the filter."""
    a = ADOPTED[sym]
    evs = setups(F, 'H1')
    LN = {e['t']: e['ln_h'] for e in evs}                       # setup time -> hours from the left shoulder to the neck
    r = run_variant(F, 'H1', a['stop'], a['exit'], entry_bar=entry_bar, events=evs)
    ok = lambda x: adopted_filter(x, a['side'], LN.get(x['setup_t']) if a.get('ln') else None)
    tr = r['trades']
    if len(tr):
        tr = tr[[ok(dict(tag=t, side=s, setup_t=u)) for t, s, u in zip(tr.tag, tr.side, tr.setup_t)]].reset_index(drop=True)
    return dict(trades=tr, open=[p for p in r['open'] if ok(p)], pending=[p for p in r['pending'] if ok(p)])
