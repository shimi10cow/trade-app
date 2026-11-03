import pandas as pd, numpy as np, glob
SPLIT={'EURUSD':'2016','USDJPY':'2016','XAUUSD':'2016','XAGUSD':'2016','US30':'2020-07','US500':'2021-10','JP225':'2021-10','BTCUSD':'2022'}
d=pd.concat([pd.read_pickle(f) for f in glob.glob('regime/ce_*.pkl')],ignore_index=True)
d['half']=[1 if t<pd.Timestamp(SPLIT[s]) else 2 for s,t in zip(d.sym,d.t)]
d['ctx']=np.select([d.W_in&d.D_in, d.WM==-d.side, d.WM==d.side],['長期レンジ','週足の調整','週足と同じ向き'],'週足なし')
X=pd.read_pickle('full/current.pkl'); mo=X.assign(Rw=X.R*X.w).groupby(X.exit_t.dt.to_period('M')).Rw.sum()
bad=set(mo[mo<=mo.quantile(0.2)].index)
def st(g):
    r=g.R.to_numpy(); hs=g.groupby(['sym','half']).R.mean(); m=g.groupby(g.exit_t.dt.to_period('M')).R.sum()
    j=pd.concat([m,mo],axis=1).fillna(0); j=j[j.index>=pd.Period('2006-01','M')]
    inbad=g[g.exit_t.dt.to_period('M').isin(bad)].R.sum()
    return pd.Series(dict(n_yr=len(r)/21.4,win=(r>0).mean(),h1=g[g.half==1].R.mean(),h2=g[g.half==2].R.mean(),pos=int((hs>0).sum()),cells=len(hs),PF=r[r>0].sum()/max(-r[r<0].sum(),1e-9),Ryr=r.sum()/21.4,
        corr=j.iloc[:,0].corr(j.iloc[:,1]),悪い月R=inbad,top5=np.sort(r)[::-1][:5].sum()/r.sum() if r.sum()>0 else np.nan))
S=d.groupby(['trig','ex','ctx']).apply(st)
pd.set_option('display.width',250); pd.set_option('display.max_rows',100)
print(S.round(3).to_string())
d.to_pickle('regime/ce_all.pkl')
