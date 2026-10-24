"""PB2: the user's pullback count as an EA (2026-10-22, from the labels of USDJPY 2009/2013 and EURUSD 2009).
H1 trend = H1 major Dow. A pullback is counted when a swing low (buy) forms after a new high: lowest of 3 bars on each side,
at least 1 ATR(H1) below the high (fitted to the user's labels, 60% exact agreement, 92% within one).
Setup: the k-th pullback's swing low is confirmed (k in `ks`) and the H4 major Dow points the same way (H4 filter `h4`).
Trigger: next M15 provisional Dow turn within 12h ('dow') or at once ('now'). Stop: that swing low ('ref') + 0.3 ATR, or the
M15 turn's protected low. Exit: H1 swing trail from +1R. Writes results/pb2/PB2_<...>.csv"""
import sys, os, itertools, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'pb2'; OUT.mkdir(parents=True, exist_ok=True)
X.add_trigger('now', lambda: {d: list(range(X.N)) for d in ('up', 'down')})
h1 = B.h1.reset_index(drop=True); H = h1.h.to_numpy(); L = h1.l.to_numpy(); A = np.asarray(B.A1)
D1 = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R1['bars']])
D4 = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R4['bars']])
h4 = B.h4.reset_index(drop=True); H4h = h4.h.to_numpy(); L4 = h4.l.to_numpy()
def h4_counts():
    """H4 pullback count with the H4 rule (swing 2 bars, 1.5 ATR(H4))"""
    pc = h4.c.shift(); tr = np.maximum(h4.h - h4.l, np.maximum((h4.h - pc).abs(), (h4.l - pc).abs())); A4 = tr.rolling(14).mean().bfill().to_numpy()
    n = len(h4); cnt = np.zeros(n, int); side = 0; i0 = 0; ext = 0; armed = True; c = 0
    for j in range(n):
        if D4[j] != side: side = D4[j]; i0 = j; c = 0; armed = True; ext = H4h[j] if side == 1 else L4[j]
        elif side:
            newx = (H4h[j] > ext) if side == 1 else (L4[j] < ext)
            if newx: ext = H4h[j] if side == 1 else L4[j]
            k = j - 2
            if k > i0:
                w = L4[max(i0, k - 2):j + 1] if side == 1 else H4h[max(i0, k - 2):j + 1]
                piv = (L4[k] == w.min()) if side == 1 else (H4h[k] == w.max())
                if armed and piv and (ext - L4[k] if side == 1 else H4h[k] - ext) >= 1.5 * A4[k]: c += 1; armed = False
            if not armed and newx: armed = True
        cnt[j] = c
    return cnt
C4N = h4_counts()
def events(ks, h4f, par=3, dmin=1.0):
    ev = []; side = 0; i0 = 0; ext = 0; armed = True; c = 0
    for j in range(len(h1)):
        if D1[j] != side: side = D1[j]; i0 = j; c = 0; armed = True; ext = H[j] if side == 1 else L[j]; continue
        if not side: continue
        newx = (H[j] > ext) if side == 1 else (L[j] < ext)
        if newx: ext = H[j] if side == 1 else L[j]
        k = j - par
        if k > i0:
            w = L[max(i0, k - par):j + 1] if side == 1 else H[max(i0, k - par):j + 1]
            piv = (L[k] == w.min()) if side == 1 else (H[k] == w.max())
            if armed and piv and (ext - L[k] if side == 1 else H[k] - ext) >= dmin * A[k]:
                c += 1; armed = False
                if c in ks:
                    t = B.C1[j]; k4 = bisect.bisect_right(B.C4, t) - 1
                    if k4 < 0: continue
                    ok = True
                    if h4f != 'any': ok = D4[k4] == side
                    if h4f == 'n13': ok = ok and 1 <= C4N[k4] <= 3
                    if h4f == 'n0': ok = ok and C4N[k4] == 0
                    if ok: ev.append(dict(t=t, side=side, tag=f'pb{c}', ref=L[k] if side == 1 else H[k], win=12))
        if not armed and newx: armed = True
    return ev
def run1(cfg):
    ks, h4f, trig, stop, ex = cfg
    tr = X.run(events(ks, h4f), dict(trig=trig, stop=stop, buf=0.3, exit=ex, act=1.0, win=12))
    name = f"PB2_{''.join(map(str, ks))}_{h4f}_{trig}_{stop}_{ex}"; tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, len(tr), round(tr.R.sum(), 1) if len(tr) else 0
if __name__ == '__main__':
    G = list(itertools.product(((1,), (1, 2), (2,), (1, 2, 3)), ('any', 'same', 'n13'), ('dow', 'now'), ('ref', 'm15turn'), ('h1',)))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for r in p.imap_unordered(run1, G): print(*r, flush=True)
