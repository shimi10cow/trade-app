"""Original stochastic EA (research/core/engine_m15.py, canonical config: long MA, P1/P2, q75, H1 SMA200 stop, ZigZag trail) on one instrument."""
import sys, os, zipfile, pandas as pd, numpy as np
sym=sys.argv[1]
src=open('/home/user/trendlab/bars.py').read().split('for sym in')[0]
exec(src)
cache=f'/home/user/trendlab/stoch/m15_{sym}.pkl'
if not os.path.exists(cache):
    d=raw(sym).set_index('time')
    m=d.resample('15min',label='left',closed='left').agg(dict(open='first',high='max',low='min',close='last')).dropna().reset_index()
    m=m[m.time>='2004-06-01']
    if sym in ('XAUUSD','US500','JP225','OIL','NGAS'):
        for z in ('open','high','low','close'): m[z]=np.log(m[z])
    m.to_pickle(cache)
os.environ['EA_M15_CACHE']=cache
sys.path.insert(0,'/home/user/trade-app/research/core')
import engine_m15 as EM
res=EM.run_pair(sym)
tr=res[0] if isinstance(res,tuple) else res
pd.DataFrame(tr).to_pickle(f'/home/user/trendlab/stoch/tr_{sym}.pkl'); print('done',sym,len(tr))
