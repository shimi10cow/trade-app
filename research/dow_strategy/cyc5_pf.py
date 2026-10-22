import numpy as np, pandas as pd
from pfx import ev, BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_feat2.pkl')
ev(A, BASE9T2, label='9本T2（基準）')
for k in BASE9T2:
    ev(A, [x for x in BASE9T2 if x != k], label=f'- {k} を外す')
for k in ('S@BTCUSD', 'J2@BTCUSD', 'L@XAUUSD', 'J3@USDJPY', 'EV@EURUSD', 'C@XAUUSD', 'J2@EURUSD', 'P@XAUUSD'):
    ev(A, BASE9T2 + [k], label=f'+ {k}')
