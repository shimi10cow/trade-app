import pandas as pd, numpy as np, glob, sys
sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr
LOG={'XAUUSD','XAGUSD','US500','JP225'}
x=pd.concat([pd.read_pickle(f) for f in glob.glob('ev_*.pkl')]); x=x[x.kind!='基準H4向き']; x['t']=pd.to_datetime(x.t)
rows=[]
for sym,g in x.groupby('sym'):
    h=pd.read_pickle(f'/home/user/trendlab/h1_{sym}.pkl')[['t','o','h','l','c']].reset_index(drop=True)
    if sym in LOG:
        for z in 'ohlc': h[z]=np.log(h[z])
    h=h[h.t>='2005-01-01'].reset_index(drop=True); C1=h.t+pd.Timedelta('1h'); hi,lo,c=(h[z].to_numpy() for z in 'hlc'); n=len(c)
    A=pd.Series(atr(h)).rolling(500,min_periods=50).mean().to_numpy()
    for _,r in g.iterrows():
        i=int(C1.searchsorted(r.t)); s=r.s
        for j in range(i+1,min(n-241,i+25)):
            ok=(c[j]>hi[j-3:j].max()) if s==1 else (c[j]<lo[j-3:j].min())
            if ok:
                f={k:s*(c[j+H]-c[j])/A[j] for k,H in (('g24',24),('g72',72),('g240',240))}
                rows.append(dict(sym=sym,kind=r.kind,t=r.t,s=s,dside=r.dside,d1=r.d1,**f)); break
y=pd.DataFrame(rows); y.to_pickle('conf.pkl')
DEV=['EURUSD','XAUUSD','US500']; y['late']=y.t.dt.year>=2016
for lab,m in [('条件なし',y.s==y.s),('日足側＋D1ダウ',(y.dside==1)&(y.d1==1))]:
    print(lab)
    for k,g in y[m].groupby('kind'):
        print(' ',k.ljust(6),len(g),' 順方向 24/72/240:',[f"{(g[c]>0).mean()*100:.0f}%" for c in ('g24','g72','g240')],
              ' f72:',' '.join(f"{n}:{(g[pm.loc[g.index]].g72>0).mean()*100:.0f}%" for n,pm in [('dev',y.sym.isin(DEV)),('他',~y.sym.isin(DEV)),('前',~y.late),('後',y.late)]))
