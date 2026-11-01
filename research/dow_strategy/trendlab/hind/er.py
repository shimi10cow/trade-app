import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab')
from lab import load
X=pd.read_pickle('feat_box.pkl'); out=[]
for sym,g in X.groupby('sym'):
    h,_=load(sym); h=h.reset_index(drop=True); c=h.c.to_numpy(float); T=pd.to_datetime(h.t); ad=np.r_[0,np.cumsum(np.abs(np.diff(c)))]
    idx=T.searchsorted(g.t)
    for (k,r),i in zip(g.iterrows(),idx):
        i0=i-int(r.since); f={'_k':k}
        for L in (75,300,500):
            a=max(0,i0-L); f[f'er{L}']=abs(c[i0]-c[a])/max(1e-12,ad[i0]-ad[a])
        out.append(f)
X=X.join(pd.DataFrame(out).set_index('_k')); X.to_pickle('feat_box2.pkl')
