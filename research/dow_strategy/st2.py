"""Wider search for the gold/BTC trend EA (S) — 2026-10-22. Same setup/trigger as st_trend.py (M15 Dow turn while
H4 and H1 trends agree) with more choices: stop (H1 swing + 0.3/0.8 ATR, M15 turn + 0.3 ATR) and exit (H1 trail from
+1R or +2R, H4 swing trail from +1R, hybrid M15->H1). Output results/st2/S_<c4>_<c1>_<side>_<stop>_<exit>.csv.
Selection must be made on the instrument's first half only."""
import sys, os, itertools
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import st_trend as ST  # noqa: E402
X = ST.X
OUT = ST.B.HERE / 'results' / 'st2'; OUT.mkdir(exist_ok=True, parents=True)
STOPS = {'sw3': ('h1swing', 0.3), 'sw8': ('h1swing', 0.8), 'mt3': ('m15turn', 0.3)}
EXITS = {'h1a1': ('h1', 1.0), 'h1a2': ('h1', 2.0), 'h4a1': ('h4', 1.0), 'hyb': ('hyb', 1.0)}


def run1(c):
    c4, c1, side, st, ex = c
    name = f'S_{c4}_{c1}_{side}_{st}_{ex}'
    if (OUT / f'{name}.csv').exists():
        return name, -1
    cfg = dict(trig='dow', stop=STOPS[st][0], buf=STOPS[st][1], exit=EXITS[ex][0], act=EXITS[ex][1], sw=2.0, win=1)
    if side in ('both_d', 'buy_d'):
        cfg['dside'] = 0
    tr = X.run(ST.events(c4, c1, side), cfg)
    tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, len(tr)


if __name__ == '__main__':
    G = list(itertools.product(('ma', 'prov'), ('ma', 'prov'), ('buy', 'buy_d', 'both_d'), list(STOPS), list(EXITS)))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for name, n in p.imap_unordered(run1, G):
            print(name, n, flush=True)
