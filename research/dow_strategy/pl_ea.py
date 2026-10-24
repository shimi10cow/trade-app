"""PL: bounce at the H4 protected level in an H4 trend (2026-10-22, user: 'in a trend, a deeper H4 correction back to the
押し安値 — how much do we take that bounce?'). Event study: price holds there 57-63 % (2 ATR away before a close 0.5 ATR
beyond) on EURUSD/GBPUSD/EURJPY/gold/BTC in both halves (USDJPY ~50 %).
Setup: an H4 bar closes with its low within `near` x ATR(H4) of the H4 major 押し安値 (buy; mirror for sell) and the close
still above it. Trigger: M15 provisional turn within 12h ('dow') or next M15 open ('now'). Stop: the protected level -
buf x ATR(H1). Exit: H1 or H4 swing trail from +1R."""
import sys, os, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'pl'; OUT.mkdir(parents=True, exist_ok=True)
X.add_trigger('now', lambda: {d: list(range(X.N)) for d in ('up', 'down')})
h4 = B.h4.reset_index(drop=True); H = h4.h.to_numpy(); L = h4.l.to_numpy(); Cc = h4.c.to_numpy()
pc = h4.c.shift(); A4 = np.maximum(h4.h - h4.l, np.maximum((h4.h - pc).abs(), (h4.l - pc).abs())).rolling(14).mean().bfill().to_numpy()
BARS = B.R4['bars']
def events(near):
    ev = []; last = {1: -99, -1: -99}
    for j in range(20, len(h4)):
        tr, prot = BARS[j]
        if tr not in ('up', 'down') or prot is None: continue
        s = 1 if tr == 'up' else -1
        if j - last[s] < 6: continue
        ok = (L[j] <= prot + near * A4[j] and Cc[j] > prot) if s == 1 else (H[j] >= prot - near * A4[j] and Cc[j] < prot)
        if ok: last[s] = j; ev.append(dict(t=B.C4[j], side=s, tag='pl', ref=prot, win=12))
    return ev
def run1(c):
    near, trig, buf, ex = c
    tr = X.run(events(near), dict(trig=trig, stop='ref', buf=buf, exit=ex, act=1.0, win=12))
    name = f'PL_{near}_{trig}_{buf}_{ex}'; tr.to_csv(OUT / f'{name}.csv', index=False); return name, len(tr), round(tr.R.sum(), 1) if len(tr) else 0
if __name__ == '__main__':
    G = list(itertools.product((0.5, 1.0), ('dow', 'now'), (0.5, 1.0), ('h1', 'h4')))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for r in p.imap_unordered(run1, G): print(*r, flush=True)
