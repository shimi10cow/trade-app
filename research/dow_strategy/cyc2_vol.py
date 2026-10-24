"""Size up entries made in a quiet market (ATR(H1) low vs its own past 1000 bars) — compared at the same risk of ruin."""
import numpy as np, pandas as pd
from pfx import ev, BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_mkt.pkl')
TR = ['USDJPY', 'XAUUSD', 'BTCUSD']
cuts = {p: g[g.half == 1].vol_h1.quantile([.2, .4]).to_numpy() for p, g in A.groupby('pair')}
q20 = A.pair.map(lambda p: cuts[p][0]); q40 = A.pair.map(lambda p: cuts[p][1])
ev(A, BASE9T2, label='9本T2（基準）')
for lab, w in (('トレンド型 静か×1.5', np.where(A.pair.isin(TR) & (A.vol_h1 < q20), 1.5, 1.0)),
               ('トレンド型 静か×2', np.where(A.pair.isin(TR) & (A.vol_h1 < q20), 2.0, 1.0)),
               ('全通貨 静か×1.5', np.where(A.vol_h1 < q20, 1.5, 1.0)),
               ('トレンド型 静か×1.5 やや静か×1.25', np.where(A.pair.isin(TR) & (A.vol_h1 < q20), 1.5, np.where(A.pair.isin(TR) & (A.vol_h1 < q40), 1.25, 1.0))),
               ('トレンド型 1/vol (0.5-2)', np.where(A.pair.isin(TR), np.clip(1 / A.vol_h1, 0.5, 2), 1.0)),
               ('全通貨 1/vol (0.5-2)', np.clip(1 / A.vol_h1, 0.5, 2))):
    B = A.copy(); B['R'] = B.R * w; ev(B, BASE9T2, label=lab)
