"""Every adopted live EA (mt5_ea/live/registry.py) on the full history of one symbol, research price space."""
import sys, time, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from mt5_ea.live.env import Env
from mt5_ea.live.registry import ADOPTED
sym=sys.argv[1]; t0=time.time()
m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
if sym=='USDJPY':
    for z in 'ohlc': m[z]=m[z]/100
start=str(max(pd.Timestamp('2005-06-01'),m.t.iat[0]+pd.Timedelta(days=250)).date())
F=Frames(m,start,h_days=10000,m_days=10000); env=Env(F.m15_all); print('frames',round(time.time()-t0),flush=True)
out=[]
for e in [x for x in ADOPTED if x.symbol==sym]:
    try:
        r=e.run(F,env); tr=pd.DataFrame(r['trades'])
        if not len(tr): print(e.key,'0'); continue
        tc=[c for c in ('t','time','entry_t') if c in tr][0]; ec=[c for c in ('exit_t','ExitTime') if c in tr][0]
        x=pd.DataFrame(dict(key=e.key,sym=sym,t=pd.to_datetime(tr[tc]),exit_t=pd.to_datetime(tr[ec]),R=tr['R'].astype(float),weight=e.weight,side=tr['side'].astype(int)))
        x=x[x.t>=pd.Timestamp(start)]
        if e.key.startswith('S@BTC'): x=x[x.t.dt.dayofweek<5]
        out.append(x); print(e.key,len(x),round(x.R.mean(),3),round(time.time()-t0),flush=True)
    except Exception as ex:
        import traceback; traceback.print_exc(); print('FAIL',e.key,ex,flush=True)
if out: pd.concat(out).to_pickle(f'/home/user/trendlab/port/p_{sym}.pkl')
print('done',sym,round(time.time()-t0),flush=True)
