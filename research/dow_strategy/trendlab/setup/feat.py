import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr
from lab import load
X=pd.read_pickle('/home/user/trendlab/x_all.pkl'); X=X[(X.sym!='XAGUSD')&(X.k<=2)].reset_index(drop=True); X['t']=pd.to_datetime(X.t); X['cross_t']=pd.to_datetime(X.cross_t)
def rs(h,rule): return h.set_index('t').resample(rule,label='left',closed='left').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index()
out=[]
for sym,g in X.groupby('sym'):
    h,_=load(sym); h=h.reset_index(drop=True); c=h.c.to_numpy(float); hi=h.h.to_numpy(float); lo=h.l.to_numpy(float); T=pd.to_datetime(h.t); n=len(c)
    A1=pd.Series(atr(h)).rolling(500,min_periods=50).mean().to_numpy(); a1=atr(h)
    m20=pd.Series(c).rolling(20).mean().to_numpy(); m75=pd.Series(c).rolling(75).mean().to_numpy()
    h4=rs(h,'4h'); A4=pd.Series(atr(h4)).rolling(100,min_periods=20).mean().to_numpy(); C4=h4.t+pd.Timedelta('4h'); H4h=h4.h.to_numpy(); H4l=h4.l.to_numpy(); H4c=h4.c.to_numpy()
    d1=rs(h,'1D'); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True); AD=pd.Series(atr(d1)).rolling(50,min_periods=10).mean().to_numpy(); CD=d1.t+pd.Timedelta('1D')
    Dh=d1.h.to_numpy(); Dl=d1.l.to_numpy(); Dc=d1.c.to_numpy()
    for idx,r in g.iterrows():
        i=int(T.searchsorted(r.t)); i0=int(T.searchsorted(r.cross_t)); s=r.s
        k0=int(C4.searchsorted(r.cross_t,side='right'))-1; k=int(C4.searchsorted(r.t+pd.Timedelta('1h'),side='right'))-1
        kd=int(CD.searchsorted(r.t+pd.Timedelta('1h'),side='right'))-1
        if k0<100 or kd<60: continue
        f=dict(_i=idx)
        f['sl75']=(m75[i]-m75[i-10])*s/a1[i]; f['sl20']=(m20[i]-m20[i-10])*s/a1[i]
        f['d20']=(lo[i]-m20[i])/a1[i] if s==1 else (m20[i]-hi[i])/a1[i]
        for N in (30,60):
            bh=H4h[k0-N:k0].max(); bl=H4l[k0-N:k0].min(); f[f'b4w{N}']=(bh-bl)/A4[k0]
            ext=bh if s==1 else bl
            f[f'b4brk{N}']=float((H4c[k]-ext)*s>0)       # last closed H4 close beyond the pre-cross H4 box
            f[f'b4er{N}']=abs(H4c[k0]-H4c[k0-N])/np.abs(np.diff(H4c[k0-N:k0+1])).sum()
        f['h4run']=(H4c[k0-30]-H4c[k0-90])*s/A4[k0]       # trend before the box (in direction)
        f['h4run_abs']=abs(H4c[k0-30]-H4c[k0-90])/A4[k0]
        f['dw20']=(Dh[kd-19:kd+1].max()-Dl[kd-19:kd+1].min())/AD[kd]
        f['der20']=abs(Dc[kd]-Dc[kd-20])/np.abs(np.diff(Dc[kd-20:kd+1])).sum()
        f['dbrk']=float(max(((Dc[j]-Dh[j-20:j].max())*s if s==1 else (Dl[j-20:j].min()-Dc[j])) for j in range(kd-9,kd+1))>0)
        f['dpos']=((Dc[kd]-Dl[kd-19:kd+1].min())/(Dh[kd-19:kd+1].max()-Dl[kd-19:kd+1].min())); f['dpos']=f['dpos'] if s==1 else 1-f['dpos']
        for H in (24,72,240): f[f'f{H}']=s*(c[min(n-1,i+H)]-c[i])/A1[i] if i+H<n else np.nan
        e=min(n,i+241); f['mfe']=((hi[i+1:e].max()-c[i]) if s==1 else (c[i]-lo[i+1:e].min()))/A1[i]; f['mae']=((c[i]-lo[i+1:e].min()) if s==1 else (hi[i+1:e].max()-c[i]))/A1[i]
        out.append(f)
F=pd.DataFrame(out).set_index('_i'); X=X.join(F,how='inner'); X.to_pickle('/home/user/trendlab/setup/feat.pkl'); print('done',len(X))
