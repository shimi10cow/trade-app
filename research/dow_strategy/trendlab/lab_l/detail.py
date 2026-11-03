import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.eas import l as LL
S = ('EURUSD', 'USDJPY', 'XAUUSD')
base_rows = []
for s in S:
    d = pd.read_pickle(f'l_{s}.pkl'); d = d[(d.t >= '2005-06-01') & (d.entry == 'T') & (d.stop == 'W10')]
    d = d[(d.n.between(3, 4)) & (d.agree == 1) & (d.angle >= 0.03) & (d.depth.between(0.3, 0.85)) & (d.tri == 0) & (d.sd > 0)]
    if s == 'XAUUSD':
        F = pickle.load(open(f'/home/user/trendlab/live_frames_{s}.pkl', 'rb')); T = F.M15T
        ent = {t: F.o[int(T.searchsorted(t))] for t in d.t.unique()}
        d['room'] = [LL.room_h4(F, t, sd_, ent[t]) for t, sd_ in zip(d.t, d.side)]
    base_rows.append(d)
pd.concat(base_rows).to_pickle('detail_base.pkl'); print('ok')
