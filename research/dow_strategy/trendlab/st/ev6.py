import pandas as pd, numpy as np, sys
d=pd.read_pickle(sys.argv[1])
def st(g):
    r=g.R; yrs=21.5; eq=g.sort_values('t').R.cumsum()
    return pd.Series(dict(n_yr=len(g)/yrs,h1=g[g.half==1].R.mean(),h2=g[g.half==2].R.mean(),EUR=g[g.sym=='EURUSD'].R.mean(),XAU=g[g.sym=='XAUUSD'].R.mean(),
        PF=r[r>0].sum()/-r[r<0].sum(),win=(r>0).mean(),R_yr=r.sum()/yrs,DD=(eq-eq.cummax()).min(),cost=g.cR.mean(),gross=g.R0.mean(),hold_h=g.mins.median()/60,wid=g.wid.median()))
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
print(d.groupby('cfg').apply(st).sort_values('R_yr',ascending=False).round(3).to_string())
