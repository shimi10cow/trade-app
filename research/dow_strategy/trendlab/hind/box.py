import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr as atr7
from lab import load
X=pd.read_pickle('feat_no75b.pkl'); out=[]
for sym,g in X.groupby('sym'):
    h,_=load(sym); h=h.reset_index(drop=True); hi,lo,c=(h[z].to_numpy(float) for z in 'hlc'); A=np.asarray(atr7(h)); T=pd.to_datetime(h.t)
    A5=pd.Series(A).rolling(500,min_periods=100).mean().to_numpy()
    idx=T.searchsorted(g.t)
    for (k,r),i in zip(g.iterrows(),idx):
        s=r.s; i0=i-int(r.since); a=A5[i0]; f={'_k':k}
        a0=max(0,i0-600)
        rh=np.maximum.accumulate(hi[a0:i0+1][::-1]); rl=np.minimum.accumulate(lo[a0:i0+1][::-1]); w=(rh-rl)/a   # width of [i0-L, i0]
        for W in (6,8,10,12):
            ok=np.flatnonzero(w>W); L=int(ok[0]) if len(ok) else len(w); f[f'len{W}']=L
            if L>=20:
                top=rh[L-1] if s==1 else -rl[L-1]; top=rh[L-1] if s==1 else rl[L-1]
                f[f'brk{W}']=float((c[i]-top)*s>0); f[f'out{W}']=(c[i]-top)*s/a
            else: f[f'brk{W}']=np.nan; f[f'out{W}']=np.nan
        for L in (100,200,300):
            f[f'w{L}']=w[min(L,len(w)-1)]
        out.append(f)
F=pd.DataFrame(out).set_index('_k'); X=X.join(F); X.to_pickle('feat_box.pkl'); print('done')
