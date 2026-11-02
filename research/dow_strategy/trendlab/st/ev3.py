import pandas as pd, numpy as np, warnings, sys; warnings.filterwarnings('ignore')
cfg=sys.argv[1]; pat=sys.argv[2] if len(sys.argv)>2 else 'r3'
rows=[]
CO={'EURUSD':1.2e-4,'USDJPY':1.5e-2,'XAUUSD':2.5e-4,'US30':1.5e-4,'US500':2e-4,'JP225':3e-4}
for s in CO:
    d=pd.read_pickle(f'{pat}_{s}.pkl'); d=d[d.cfg==cfg].reset_index(drop=True)
    f=pd.read_pickle(f'f_{s}.pkl'); fi=f.set_index('time'); x=fi.loc[d.t]; sd=d.side.values
    d['op']=x.op4.values*sd; d['sl4']=x.sl4.values*sd; d['h1sl']=x.h1sl.values*sd; d['er']=x.h1er.values
    d['m20d']=(x.c.values-x.h1m20.values)*sd/x.h1a.values; d['m75d']=(x.c.values-x.h1m75.values)*sd/x.h1a.values
    p=((x.c-x.h1lo)/(x.h1hi-x.h1lo)).values; d['pos']=np.where(sd==1,p,1-p)
    d['vol']=(fi.a15/fi.a15.rolling(96*20).mean()).loc[d.t].values; d['a15h1']=(x.a15/x.h1a).values
    d['m2075']=((x.m20-x.m75)*sd/x.a15).values
    d['R']=d.R0-d.cR; rows.append(d)
d=pd.concat(rows,ignore_index=True)
print('n',len(d),'R',d.R.mean().round(3), d.groupby('half').R.mean().round(3).to_dict(),'cost',d.cR.mean().round(3))
for col in ['op','sl4','h1sl','er','m20d','m75d','pos','vol','a15h1','m2075']:
    q=pd.qcut(d[col].rank(method='first'),5,labels=False)
    t=d.groupby([q,'half']).R.mean().unstack().round(3).T; t.loc['lo']=d.groupby(q)[col].min().round(2); print(col,'\n',t.to_string())
r=d.sort_values('R',ascending=False)
print(d.groupby(['sym','half']).R.agg(['mean','count']).unstack().round(3))
print('top10 share',(r.R.head(10).sum()/d.R.sum()).round(2),'cost1.5x',(d.R0-1.5*d.cR).groupby(d.half).mean().round(3).to_dict())
d.to_pickle(f'/home/user/trendlab/st/ev_{pat}.pkl')
