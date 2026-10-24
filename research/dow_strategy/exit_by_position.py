"""Exit chosen by where the trade sits in the H4 trend (2026-10-22). For EAs run with 6 exits (exit_by_pair.py), each
trade's H4 progress at entry (pushes since the H4 major turn, wave_features.py) picks the exit:
  early (0-1 pushes) -> one exit, middle (2) -> base, late (3+) or against H4 -> another exit.
Entries are matched across the exit files by entry time and side."""
import numpy as np, pandas as pd
from pathlib import Path
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
D = {'EURUSD': Path('/home/user/trade-app/research/dow_strategy/results/exits'), 'USDJPY': Path(f'{S}/jpy/research/dow_strategy/results/exits')}
for p in ('EURJPY', 'GBPUSD', 'XAUUSD', 'BTCUSD'): D[p] = Path(f'{S}/ws_{p}/research/dow_strategy/results/exits')
SPLIT = {'BTCUSD': ((2017, 2021), (2022, 2026))}; COST = {'XAUUSD': 2.5, 'BTCUSD': 8.0}
EX = ['base', 'm15a05', 'm15a1', 'hyb', 'h1a2', 'h4a1']
rows = []
for sym, d in D.items():
    h1, h2 = SPLIT.get(sym, ((2005, 2015), (2016, 2026)))
    W = pd.read_csv(f'{S}/feat/wave_{sym}.csv', parse_dates=['t']) if False else None
    for ea in ('J2', 'J3', 'EV', 'C', 'P', 'S'):
        if not (d / f'{ea}_base.csv').exists(): continue
        X = None
        for ex in EX:
            x = pd.read_csv(d / f'{ea}_{ex}.csv', parse_dates=['t'])[['t', 'side', 'R', 'risk']]
            x['R'] = x.R - (COST.get(sym, 1.2) - 1.2) * 1e-4 / x.risk
            x = x.drop_duplicates(['t', 'side']).rename(columns={'R': ex}).drop(columns='risk')
            X = x if X is None else X.merge(x, on=['t', 'side'], how='inner')
        rows.append(X.assign(sym=sym, ea=ea))
A = pd.concat(rows, ignore_index=True)
print('rows', len(A))
A.to_pickle(f'{S}/feat/exit_matrix.pkl')
