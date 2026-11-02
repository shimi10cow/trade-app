import pandas as pd, numpy as np, glob
d=pd.concat([pd.read_pickle(f) for f in glob.glob('r9_*.pkl')],ignore_index=True)
def st(g):
    r=g.R.to_numpy(); s=np.sort(r)[::-1]; e=np.cumsum(g.sort_values('t').R.to_numpy()); dd=(e-np.maximum.accumulate(np.r_[0,e])[1:]).min()
    hs=g.groupby(['sym','half']).R.mean()
    return pd.Series(dict(n_yr=len(g)/21.4,h1=g[g.half==1].R.mean(),h2=g[g.half==2].R.mean(),EUR=g[g.sym=='EURUSD'].R.mean(),XAU=g[g.sym=='XAUUSD'].R.mean(),JPY=g[g.sym=='USDJPY'].R.mean(),
        symhalf_pos=int((hs>0).sum()),PF=r[r>0].sum()/-r[r<0].sum(),win=(r>0).mean(),R_yr=r.sum()/21.4,ex5=s[5:].sum()/21.4,DD=dd,top5=s[:5].sum()/r.sum()))
pd.set_option('display.width',260); pd.set_option('display.max_rows',100)
for lab,m in [('絞りなし',d.ep>=0),('押し1〜2回目',d.ep<=2),('深さ≥35%',d.depth>=.35),('1〜2回目＋深さ≥35%',(d.ep<=2)&(d.depth>=.35))]:
    print('\n==',lab); print(d[m].groupby('cfg').apply(st).round(3).sort_values('R_yr',ascending=False).to_string())
