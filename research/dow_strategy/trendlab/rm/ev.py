import pandas as pd, numpy as np, glob
SPLIT={'EURUSD':'2016','USDJPY':'2016','XAUUSD':'2016','XAGUSD':'2016','US30':'2020-07','US500':'2021-10','JP225':'2021-10','BTCUSD':'2022'}
d=pd.concat([pd.read_pickle(f) for f in glob.glob('rm/r_*.pkl')],ignore_index=True)
d['half']=[1 if t<pd.Timestamp(SPLIT[s]) else 2 for s,t in zip(d.sym,d.t)]
def st(g):
    r=g.R.to_numpy(); hs=g.groupby(['sym','half']).R.mean(); s=np.sort(r)[::-1]
    return pd.Series(dict(n_yr=len(r)/21.4,win=(r>0).mean(),h1=g[g.half==1].R.mean(),h2=g[g.half==2].R.mean(),pos=int((hs>0).sum()),cells=len(hs),
        PF=r[r>0].sum()/max(-r[r<0].sum(),1e-9),Ryr=r.sum()/21.4,t=r.mean()/(r.std()/np.sqrt(len(r))),top5=s[:5].sum()/r.sum() if r.sum()>0 else np.nan))
out=[]
for dep in (1.0,1.5,2.0):
    S=d[d.peak>=dep].groupby(['kind','trig','stop','ex']).apply(st); S['dep']=dep; out.append(S.reset_index())
S=pd.concat(out); pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
print(S.sort_values('t',ascending=False).head(30).round(2).to_string(index=False))
print('\n全体: t>2.5 の設定', (S.t>2.5).sum(), '/', len(S))
S.to_pickle('rm/S.pkl')
