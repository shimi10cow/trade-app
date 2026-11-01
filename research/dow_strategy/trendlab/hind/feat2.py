import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr as atr7
from lab import load
X=pd.read_pickle('feat_no75.pkl'); X['t']=pd.to_datetime(X.t); out=[]
for sym,g in X.groupby('sym'):
    h,_=load(sym); h=h.reset_index(drop=True); c=h.c.to_numpy(float); A=np.asarray(atr7(h)); T=pd.to_datetime(h.t)
    m20=pd.Series(c).rolling(20).mean().to_numpy(); m75=pd.Series(c).rolling(75).mean().to_numpy()
    A50=pd.Series(A).rolling(50).mean().to_numpy()
    idx=T.searchsorted(g.t)
    for (k,r),i in zip(g.iterrows(),idx):
        s=r.s; i0=i-int(r.since); a=A50[i]
        sp=lambda j:(m20[j]-m75[j])*s/a
        f=dict(sl75=(m75[i]-m75[i-10])*s/a, sl20=(m20[i]-m20[i-10])*s/a, sl75x=(m75[i]-m75[i0])*s/a,
               spread=sp(i), widen=sp(i)-sp(i-10), sp_max=max(sp(j) for j in range(i0,i+1)), sp_ratio=sp(i)/max(1e-9,max(sp(j) for j in range(i0,i+1))))
        f['_k']=k; out.append(f)
F=pd.DataFrame(out).set_index('_k'); X=X.join(F); X.to_pickle('feat_no75b.pkl'); print('done',len(X))
