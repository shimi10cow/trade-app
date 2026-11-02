import pandas as pd, numpy as np, warnings; warnings.filterwarnings('ignore')
import sys
cfgs=sys.argv[1].split(',')
rows=[]
for s in ['XAUUSD','EURUSD','USDJPY','US30','US500','JP225']:
    d=pd.read_pickle(f'r1_{s}.pkl'); d=d[d.cfg.isin(cfgs)]
    f=pd.read_pickle(f'f_{s}.pkl').set_index('time')
    x=f.loc[d.t]; d=d.reset_index(drop=True)
    sd=d.side.values
    d['hr']=d.t.dt.hour; d['wid']=(1/d.cR)*{'EURUSD':1.2e-4,'USDJPY':1.5e-2}.get(s,{'XAUUSD':2.5e-4,'US30':1.5e-4,'US500':2e-4,'JP225':3e-4}.get(s))/x.a15.values
    d['costR']=d.cR; d['op']=x.op4.values*sd; d['h1sl']=x.h1sl.values*sd; d['er']=x.h1er.values
    d['m20d']=(x.c.values-x.h1m20.values)*sd/x.h1a.values; d['pos']=((x.c-x.h1lo)/(x.h1hi-x.h1lo)).values; d['pos']=np.where(sd==1,d.pos,1-d.pos)
    d['a15rel']=(x.a15/x.h1a).values; d['vol']=(x.a15/x.a15.rolling(96*20).mean()).values
    d['R']=d.R0-d.cR; rows.append(d)
d=pd.concat(rows)
for col in ['costR','wid','op','h1sl','er','m20d','pos','vol']:
    d['q']=pd.qcut(d[col].rank(method='first'),5,labels=False)
    t=d.groupby(['q','half']).R.mean().unstack().round(3); t['R0']=d.groupby('q').R0.mean().round(3); t['lo']=d.groupby('q')[col].min().round(2)
    print(col); print(t.T.to_string())
print(d.groupby(['sym','half']).R.mean().unstack().round(3))
