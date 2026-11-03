import sys, pickle, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.core import Frames
s = sys.argv[1]
m = pd.read_pickle(f'/home/user/trendlab/stoch/m15_{s}.pkl').rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
if s.endswith('JPY'):
    for z in 'ohlc': m[z] = m[z] / 100
F = Frames(m, '2005-01-01', h_days=10000, m_days=10000); pickle.dump(F, open(f'/home/user/trendlab/live_frames_{s}.pkl', 'wb')); print(s, 'ok', flush=True)
