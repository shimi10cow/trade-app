"""RM on broker-time Frames, 11 pairs, a few principled variants (2026-11-04)."""
import pickle, sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.eas import rm as RM
sym = sys.argv[1]
COST = {'GBPUSD': 1.5e-4, 'AUDUSD': 1.3e-4, 'USDCAD': 2e-4, 'USDCHF': 2e-4, 'EURJPY': 2e-4, 'AUDJPY': 2.5e-4, 'CADJPY': 3e-4, 'CHFJPY': 3e-4, 'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4}[sym]
F = pickle.load(open(f'/home/user/trendlab/tz/frames_{sym}.pkl', 'rb'))
V = {'今の RM': {}, '前のトレンドの条件なし': dict(pre=0), '割り込み 0.2 まで': dict(tol=0.2), '前のトレンド 100 本': dict(pre=100)}
rows = []
for k, kw in V.items():
    tr = RM.run(F, cfg=dict(RM.CFG, **kw))['trades']
    if not len(tr): continue
    tr['t'] = pd.to_datetime(tr.t); tr = tr[tr.t >= '2005-06-01']
    rows.append(pd.DataFrame(dict(sym=sym, v=k, t=tr.t, side=tr.side, R=tr.R + F.COST / tr.risk - COST / tr.risk)))
    print(sym, k, len(tr), flush=True)
pd.concat(rows).to_pickle(f'/home/user/trendlab/tz/rm_{sym}.pkl')
