"""Double top right shoulder (user idea, 2026-10-23; mirror = double bottom right shoulder).
An up trend makes its high H (left shoulder); a sharp pullback breaks the H4 (or H1) protected low = the major Dow trend
turns from up to down (known at that bar's close). Price then rallies again but, having fallen deep, tends to be sold
before H is exceeded -> sell the right shoulder. Stronger if H sits on an older resistance.
  H     : highest high of the up trend that just ended (from the trend's start to the reversal bar)
  L     : lowest low after the reversal (updated until the rally starts) = the neckline
  rally : price comes back to at least L + 0.38 x (H - L); then the first M15 provisional turn down while price stays below H
          -> entry (cancelled once a high goes above H, or 5 days after the reversal)
Tag (filtered later): tf | retr (shoulder high reached as share of H-L) | depth ((H-L)/ATR H4) | res (H within 0.5 ATR(H4)
of an older confirmed H4 swing high, 20-500 H4 bars before the trend start) | bars from reversal to entry (H1)
Stop: above the right shoulder high (shoulder) or above H (left); + 0.3 ATR(H1).
Exit: tp2 / h1 trail from +1R / neck (target = L, else 3R).
Run in a workspace; writes results/ds/DS_<tf>_<stop>_<exit>.csv"""
import os, sys, bisect, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ea_core as X  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
B = X.B
SYM = os.environ.get('M5_SYM', 'EURUSD')
OUT = B.HERE / 'results' / 'ds'; OUT.mkdir(parents=True, exist_ok=True)
CL15 = X.CL15; Mh, Ml, Mc = B.h, B.l, B.c
h4 = B.h4.reset_index(drop=True); A4 = np.asarray(atr(h4), float); C4 = pd.DatetimeIndex(B.C4)
H4P = [(e['idx'], e['available_idx'], e['kind'], e['price']) for e in B.R4['pivot_events']]
TURN = {d: sorted(e['idx'] for e in B.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d) for d in ('up', 'down')}


def events(tf):
    df, R, close = (B.h4, B.R4, B.C4) if tf == 'H4' else (B.h1, B.R1, B.C1)
    df = df.reset_index(drop=True); hi, lo = df.h.to_numpy(float), df.l.to_numpy(float); close = pd.DatetimeIndex(close)
    tr = [b[0] for b in R['bars']]; out = []
    k0 = 0
    for k in range(1, len(df)):
        if tr[k] != tr[k - 1]:
            prev, start = tr[k - 1], k0; k0 = k
            if not ((prev == 'up' and tr[k] == 'down') or (prev == 'down' and tr[k] == 'up')): continue
            s = -1 if prev == 'up' else 1                       # sell after an up trend broke, buy after a down trend broke
            Hx = hi[start:k + 1].max() if s == -1 else lo[start:k + 1].min()
            te = close[k]; k4 = C4.searchsorted(te, 'right') - 1; a4 = A4[k4] if k4 >= 0 and np.isfinite(A4[k4]) else np.nan
            # older resistance: confirmed H4 swing of the same kind, formed 20-500 H4 bars before the trend start
            ks = C4.searchsorted(close[start], 'right') - 1
            kind = 'hi' if s == -1 else 'lo'
            res = int(any(kd == kind and ks - 500 <= ix <= ks - 20 and av <= ks and abs(p - Hx) <= 0.5 * a4 for ix, av, kd, p in H4P))
            out.append(dict(te=te, side=s, H=Hx, a4=a4, res=res))
    return out


def setups(tf):
    ev = []
    for e in events(tf):
        s, Hx = e['side'], e['H']; i0 = CL15.searchsorted(e['te']); iend = min(CL15.searchsorted(e['te'] + pd.Timedelta('120h')), len(Mc) - 1)
        Lx = None; rally = None
        for i in range(i0, iend):
            if (Mh[i] > Hx) if s == -1 else (Ml[i] < Hx): break          # H exceeded: no double top
            if rally is None:
                Lx = min(Lx, Ml[i]) if (Lx is not None and s == -1) else (max(Lx, Mh[i]) if Lx is not None else (Ml[i] if s == -1 else Mh[i]))
                rng = abs(Hx - Lx)
                if rng > 0 and ((Mh[i] - Lx) if s == -1 else (Lx - Ml[i])) >= 0.38 * rng: rally = i
                continue
            lst = TURN['down' if s == -1 else 'up']
            k = bisect.bisect_left(lst, rally)
            if k < len(lst) and lst[k] < iend:
                j = lst[k]
                seg = Mh[i0:j + 1] if s == -1 else Ml[i0:j + 1]
                if (seg.max() > Hx) if s == -1 else (seg.min() < Hx): break
                sh = Mh[rally:j + 1].max() if s == -1 else Ml[rally:j + 1].min()
                retr = abs(sh - Lx) / rng
                tag = f"{tf}|{retr:.2f}|{rng / e['a4']:.2f}|{e['res']}|{(CL15[j] - e['te']) / pd.Timedelta('1h'):.0f}"
                ev.append(dict(t=CL15[j], side=s, ref_sh=sh, ref_H=Hx, neck=Lx, win=0.3, tag=tag))
            break
    return ev


EV = {tf: setups(tf) for tf in ('H4', 'H1')}
print(SYM, {k: len(v) for k, v in EV.items()}, flush=True)
X.add_trigger('all', lambda: {'up': list(range(X.N)), 'down': list(range(X.N))})


def run1(c):
    tf, stop, ex = c
    ev = [dict(e, ref=e['ref_sh'] if stop == 'shoulder' else e['ref_H'], tp_px=e['neck']) for e in EV[tf]]
    cfg = dict(trig='all', stop='ref', buf=0.3, win=0.3, one_per_side=True)
    if ex == 'h1': cfg.update(exit='h1', act=1.0)
    elif ex == 'neck': cfg.update(exit='h1', act=99, tp_px=True, tp=3.0)
    else: cfg.update(exit='h1', act=99, tp=2.0)
    tr = X.run(ev, cfg); name = f'DS_{tf}_{stop}_{ex}'
    if len(tr): tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, len(ev), len(tr), round(tr.R.sum(), 1) if len(tr) else 0


if __name__ == '__main__':
    G = list(itertools.product(('H4', 'H1'), ('shoulder', 'left'), ('tp2', 'h1', 'neck')))
    with Pool(int(os.environ.get('NPROC', '2'))) as p:
        for r in p.imap_unordered(run1, G): print(*r, flush=True)
