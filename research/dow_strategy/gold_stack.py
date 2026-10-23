"""Gold-specific: pyramiding on the S trend EA (2026-10-23). Same setups/triggers as st2's S; a new same-side entry is allowed
while every open same-side position is already past +1R (its stop trailing), up to 2 or 3 positions. Settings: the adopted
S (ma/prov/buy/mt3/h1a1) and the H4-trail versions. Writes results/st2/K<n>_<S name>.csv"""
import sys, os, itertools
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import st_trend as ST  # noqa: E402
X = ST.X
OUT = ST.B.HERE / 'results' / 'st2'
STOPS = {'sw3': ('h1swing', 0.3), 'sw8': ('h1swing', 0.8), 'mt3': ('m15turn', 0.3)}
EXITS = {'h1a1': ('h1', 1.0), 'h1a2': ('h1', 2.0), 'h4a1': ('h4', 1.0)}


def run1(c):
    k, c4, c1, side, st, ex = c
    cfg = dict(trig='dow', stop=STOPS[st][0], buf=STOPS[st][1], exit=EXITS[ex][0], act=EXITS[ex][1], sw=2.0, win=1, stack=k)
    if side in ('both_d', 'buy_d'): cfg['dside'] = 0
    tr = X.run(ST.events(c4, c1, side), cfg); name = f'K{k}_S_{c4}_{c1}_{side}_{st}_{ex}'
    tr.to_csv(OUT / f'{name}.csv', index=False); return name, len(tr), round(tr.R.sum(), 1)


if __name__ == '__main__':
    G = list(itertools.product((1, 2, 3), ('ma',), ('prov', 'ma'), ('buy',), ('mt3', 'sw3'), ('h1a1', 'h4a1')))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for r in p.imap_unordered(run1, G): print(*r, flush=True)
