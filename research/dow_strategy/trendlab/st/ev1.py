import pandas as pd, numpy as np, glob
d=pd.concat([pd.read_pickle(p) for p in glob.glob(__import__('sys').argv[1])]); d['R']=d.R0-d.cR
yrs=d.groupby('sym').t.agg(lambda x:(x.max()-x.min()).days/365.25)
g=d.groupby(['cfg','sym','half']).R.agg(['mean','count']).unstack('half')
def summ(x):
    m=x['mean']; cnt=x['count'].sum(axis=1)
    return pd.Series(dict(h1=m[1].mean(),h2=m[2].mean(),both=((m[1]>0)&(m[2]>0)).sum(),n_yr=(cnt/yrs.reindex(cnt.index.get_level_values('sym')).values).sum()))
s=g.groupby('cfg').apply(summ)
s['all']=d.groupby('cfg').R.mean()
pd.set_option('display.width',200); pd.set_option('display.max_rows',300)
print(s.sort_values('all',ascending=False).round(3).head(40))
print(s.sort_values('all',ascending=False).round(3).tail(10))
# gross (before cost)
print(d.groupby('cfg').R0.mean().sort_values(ascending=False).head(10).round(3))
print(d.groupby('cfg').cR.median().describe())
