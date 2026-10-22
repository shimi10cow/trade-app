"""Trend + stochastic EA for gold / BTC (user, 2026-10-22: turns there are often V-shaped, so M15 Dow turns come late;
stochastic pullback triggers may catch them better). Compared with the M15 Dow-turn trigger on the same setups.
Setup (checked at every H1 close, valid for the next hour): H4 trend (SMA20/75 or provisional Dow) and H1 trend (same
choices) in the trade direction. Side: both directions with the daily SMA200 side (dside), buy only, or buy + dside.
Trigger: 'stoch' (M15 %K<20 -> %K crosses %D -> %K back above 20) or 'dow' (M15 provisional turn).
Stop beyond the last H1 swing + 0.3 ATR(H1); exit = H1 swing trail from +1R. Usage: python st_trend.py [OUT_TAG]"""
import sys, os, itertools, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'st'; OUT.mkdir(exist_ok=True, parents=True)
h1 = B.h1.reset_index(drop=True); h4 = B.h4.reset_index(drop=True)
M1 = {n: h1.c.rolling(n).mean().to_numpy() for n in (20, 75)}; M4 = {n: h4.c.rolling(n).mean().to_numpy() for n in (20, 75)}
P1 = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R1['prov_bars']])
P4 = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R4['prov_bars']])
MA1 = np.sign(M1[20] - M1[75]); MA4 = np.sign(M4[20] - M4[75])
C4 = B.C4


def events(c4, c1, side):
    ev = []
    for i, t in enumerate(B.C1):
        k = bisect.bisect_right(C4, t) - 1
        if k < 0:
            continue
        a = MA4[k] if c4 == 'ma' else P4[k]; b = MA1[i] if c1 == 'ma' else P1[i]
        if a == 0 or a != b:
            continue
        s = int(a)
        if side.startswith('buy') and s != 1:
            continue
        ev.append(dict(t=t, side=s, tag=f'{c4}{c1}', win=1))
    return ev


def run1(c):
    c4, c1, trig, side = c
    cfg = dict(trig=trig, stop='h1swing', buf=0.3, exit='h1', act=1.0, win=1)
    if side in ('both_d', 'buy_d'):
        cfg['dside'] = 0
    tr = X.run(events(c4, c1, side), cfg)
    name = f'S_{c4}_{c1}_{trig}_{side}'
    tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, len(tr)


if __name__ == '__main__':
    G = list(itertools.product(('ma', 'prov'), ('ma', 'prov'), ('stoch', 'dow'), ('both_d', 'buy', 'buy_d')))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for name, n in p.imap_unordered(run1, G):
            print(name, n, flush=True)
