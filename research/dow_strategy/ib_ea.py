"""Pullback entries after an H1 trendline break, using the user's two-line view (2026-10-23).
Event = the steep H1 line (last two swings) breaks after a >= 2 ATR run ('redraw' events of h1_break_block.py), split by
whether the flatter outer line (from the move's origin) still holds:
  'in'  : outer line intact -> 60-66 % regain the old extreme within 72h -> buy the pullback in the old direction
  'out' : outer line broken too (control, ~50 %)
Entry: first M15 provisional turn back in the old direction within W hours (24 / 48), price still beyond the outer line.
Stop: 'outer' = outer line value at the break - 0.3 ATR(H1); 'low' = the extreme since the 2nd point of the steep line - 0.3 ATR.
Exit: H1 / H4 swing trail from +1R. Writes results/ib/I_<kind>_<W>_<stop>_<exit>.csv"""
import os, sys, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SYM = os.environ.get('M5_SYM', 'EURUSD')
OUT = B.HERE / 'results' / 'ib'; OUT.mkdir(parents=True, exist_ok=True)
D = pd.read_pickle(f'{S}/feat/h1blk_{SYM}.pkl'); D = D[(D['mode'] == 'redraw') & D.outer_ok.notna()]
def events(kind, W, stop):
    g = D[D.outer_ok == (kind == 'in')]
    return [dict(t=x.t, side=int(x.side), ref=(x.outer_v if stop == 'outer' else x.inner_low), win=W, tag=kind) for x in g.itertuples()
            if np.isfinite(x.outer_v if stop == 'outer' else x.inner_low)]
def run1(c):
    kind, W, stop, ex = c
    tr = X.run(events(kind, W, stop), dict(trig='dow', stop='ref', buf=0.3, win=W, exit=ex, act=1.0))
    name = f'I_{kind}_{W}_{stop}_{ex}'
    if len(tr): tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, len(tr), round(tr.R.sum(), 1) if len(tr) else 0
if __name__ == '__main__':
    G = list(itertools.product(('in', 'out'), (24, 48), ('outer', 'low'), ('h1', 'h4')))
    with Pool(int(os.environ.get('NPROC', '2'))) as p:
        for r in p.imap_unordered(run1, G): print(*r, flush=True)
