"""Index EAs on XM data (broker time) vs the research data (other time zone), same period 2017-07 on (2026-11-04)."""
import pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.env import Env
from mt5_ea.live.registry import ADOPTED
sym = sys.argv[1]; rows = []
FX = pickle.load(open(f'/home/user/trendlab/idx/frames_{sym}.pkl', 'rb')); FR = pickle.load(open(f'/home/user/trendlab/live_frames_{sym}.pkl', 'rb'))
for lab, F in (('研究データ', FR), ('XM', FX)):
    env = Env(F.m15_all)
    for e in ADOPTED:
        if e.symbol != sym or e.key.startswith('P@'): continue
        tr = e.run(F, env)['trades']
        if not len(tr): continue
        tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]; t = pd.to_datetime(tr[tc]); r = tr.R.astype(float)[(t >= '2017-07-01').to_numpy()]
        rows.append(dict(ea=e.key, data=lab, n=len(r), avg=r.mean(), t=r.mean() / (r.std(ddof=1) / np.sqrt(len(r))), tot=r.sum()))
        print(e.key, lab, len(r), f'{r.mean():+.3f}', flush=True)
pd.DataFrame(rows).to_pickle(f'/home/user/trendlab/tz/idx_{sym}.pkl'); print('done', sym)
