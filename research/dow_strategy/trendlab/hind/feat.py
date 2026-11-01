import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr as atr7
from lab import load
X=pd.read_pickle('rule_no75.pkl'); X['t']=pd.to_datetime(X.t); out=[]
for sym,g in X.groupby('sym'):
    h,d=load(sym); h=h.reset_index(drop=True); o,hi,lo,c=(h[z].to_numpy(float) for z in 'ohlc'); A=np.asarray(atr7(h)); T=pd.to_datetime(h.t)
    m20=pd.Series(c).rolling(20).mean().to_numpy(); m75=pd.Series(c).rolling(75).mean().to_numpy(); up=m20>m75
    cr=np.r_[False,up[1:]!=up[:-1]]; ccum=np.cumsum(cr)
    A100=pd.Series(A).rolling(500).mean().to_numpy()
    # daily, known at prior day close
    D=d.copy(); D['ma20']=D.c.rolling(20).mean(); D['ma75']=D.c.rolling(75).mean(); D['ma50']=D.c.rolling(50).mean()
    D['sl20']=(D.ma20-D.ma20.shift(5))/D.atr; D['er20']=(D.c-D.c.shift(20)).abs()/D.c.diff().abs().rolling(20).sum()
    D['hh20']=D.h.rolling(20).max(); D['ll20']=D.l.rolling(20).min(); D['pos']=(D.c-D.ll20)/(D.hh20-D.ll20)
    D['rng20']=(D.hh20-D.ll20)/D.atr; D['brk_up']=(D.c>=D.h.shift(1).rolling(20).max()).rolling(5).max(); D['brk_dn']=(D.c<=D.l.shift(1).rolling(20).min()).rolling(5).max()
    D=D.shift(1); di=D.index.searchsorted(g.t.dt.floor('D'),side='right')-1
    idx=T.searchsorted(g.t)
    for (_,r),i,j in zip(g.iterrows(),idx,di):
        s=r.s; i0=i-int(r.since); dr=D.iloc[j]
        if i0<200: continue
        a=i0-150; pre_hi=hi[a:i0].max(); pre_lo=lo[a:i0].min()
        er=abs(c[i0]-c[a])/np.abs(np.diff(c[a:i0+1])).sum()
        f=dict(
          d_align=float((dr.ma20>dr.ma75)==(s==1)), d_sl=dr.sl20*s, d_er=dr.er20, d_pos=dr.pos if s==1 else 1-dr.pos, d_rng=dr.rng20,
          d_brk=dr.brk_up if s==1 else dr.brk_dn, d_above50=float((dr.c-dr.ma50)*s>0),
          pre_w=(pre_hi-pre_lo)/A[i0], pre_er=er, pre_ncross=ccum[i0]-ccum[max(0,i0-300)],
          pre_broke=float(((hi[i0:i+1].max()-pre_hi) if s==1 else (pre_lo-lo[i0:i+1].min()))>0),
          vol=A[i]/A100[i], vol_cross=A[i0]/A100[i0])
        f.update(r.to_dict()); out.append(f)
pd.DataFrame(out).to_pickle('feat_no75.pkl'); print('done',len(out))
