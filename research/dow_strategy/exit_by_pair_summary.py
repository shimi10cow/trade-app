"""Summarise exit_by_pair.py: per instrument x EA, each exit's first/second-half R and PF (instrument split, costs)."""
import numpy as np, pandas as pd
from pathlib import Path
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
D = {'EURUSD': Path('/home/user/trade-app/research/dow_strategy/results/exits'), 'USDJPY': Path(f'{S}/jpy/research/dow_strategy/results/exits')}
for p in ('EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD'): D[p] = Path(f'{S}/ws_{p}/research/dow_strategy/results/exits')
SPLIT = {'BTCUSD': ((2017, 2021), (2022, 2026))}; COST = {'XAUUSD': 2.5, 'BTCUSD': 8.0}
EX = ['base', 'm15a05', 'm15a1', 'hyb', 'h1a2', 'h4a1']
NAME = {'base': '今', 'm15a05': 'M15 +0.5R', 'm15a1': 'M15 +1R', 'hyb': 'M15→H1', 'h1a2': 'H1 +2R', 'h4a1': 'H4 +1R'}
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
rows = []
for sym, d in D.items():
    h1, h2 = SPLIT.get(sym, ((2005, 2015), (2016, 2026)))
    for ea in ('J2', 'J3', 'EV', 'C', 'P', 'S'):
        if not (d / f'{ea}_base.csv').exists(): continue
        cells = []; best = None
        for ex in EX:
            x = pd.read_csv(d / f'{ea}_{ex}.csv', parse_dates=['t']); y = x.t.dt.year
            R = x.R - (COST.get(sym, 1.2) - 1.2) * 1e-4 / x.risk
            a = R[(y >= h1[0]) & (y <= h1[1])]; b = R[(y >= h2[0]) & (y <= h2[1])]
            rows.append(dict(sym=sym, ea=ea, exit=ex, a=a.sum(), pa=pf(a), b=b.sum(), pb=pf(b)))
            cells.append(f'{NAME[ex]} {a.sum():+.0f}/{b.sum():+.0f}')
        print(f'{sym} {ea:3s} | ' + ' | '.join(cells))
T = pd.DataFrame(rows); T.to_csv(f'{S}/feat/exit_by_pair.csv', index=False)
