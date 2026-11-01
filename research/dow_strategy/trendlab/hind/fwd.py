import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr as atr7
from lab import load
X=pd.read_pickle('feat_ext.pkl'); out=[]
for sym,g in X.groupby('sym'):
    h,d=load(sym); h=h.reset_index(drop=True); hi,lo,c=(h[z].to_numpy(float) for z in 'hlc'); T=pd.to_datetime(h.t)
    A=pd.Series(np.asarray(atr7(h))).rolling(500,min_periods=100).mean().to_numpy()   # slow H1 ATR as the unit
    idx=T.searchsorted(g.t); n=len(c)
    for (k,r),i in zip(g.iterrows(),idx):
        s=r.s; a=A[i]; f={'_k':k}
        for H in (24,72,240): f[f'f{H}']=s*(c[min(n-1,i+H)]-c[i])/a
        e=min(n,i+241); fav=((hi[i+1:e].max()-c[i]) if s==1 else (c[i]-lo[i+1:e].min()))/a; adv=((c[i]-lo[i+1:e].min()) if s==1 else (hi[i+1:e].max()-c[i]))/a
        f['mfe']=fav; f['mae']=adv; out.append(f)
X=X.join(pd.DataFrame(out).set_index('_k'))
X['ext']=((X.mfe>=12)&(X.mfe>2*X.mae)).astype(int)     # 伸びた: 240本で 12 ATR 以上、逆行の 2 倍以上
X.to_pickle('feat_fwd.pkl'); print('done', X.ext.mean().round(3), X[['f24','f72','f240','mfe','mae']].median().round(2).to_dict())
