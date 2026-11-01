import json, numpy as np, pandas as pd, sys
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr as atr7
K=pd.read_pickle('key.pkl').set_index('id'); M=json.load(open('marks.json'))
X=pd.read_pickle('/home/user/trendlab/x_all.pkl')
rows=[]; base=[]; cache={}
def feats(h,c,m20,m75,A,up,i,s):
    lc=np.flatnonzero((up[1:i+1]!=up[:i]))  # crosses before i
    last=lc[-1]+1 if len(lc) else 0
    cross_ok=(up[i]==(s==1))
    hi20=h.h.iloc[i-20:i].max(); lo20=h.l.iloc[i-20:i].min()
    f=dict(since=i-last, ok=cross_ok,
        slope75=(m75[i]-m75[i-10])*s/A[i], spread=(m20[i]-m75[i])*s/A[i], widen=((m20[i]-m75[i])-(m20[i-10]-m75[i-10]))*s/A[i],
        d20=(c[i]-m20[i])*s/A[i], d75=(c[i]-m75[i])*s/A[i],
        pos20=((c[i]-lo20)/(hi20-lo20) if s==1 else (hi20-c[i])/(hi20-lo20)),
        mv=(c[i]-c[last])*s/A[i] if last else np.nan)
    fut=h.iloc[i+1:i+121]
    f['mfe']=((fut.h.max()-c[i]) if s==1 else (c[i]-fut.l.min()))/A[i]; f['mae']=((c[i]-fut.l.min()) if s==1 else (fut.h.max()-c[i]))/A[i]
    return f
for w,ms in M.items():
    k=K.loc[w]; sym=k.sym
    if sym not in cache:
        h=pd.read_pickle(f'/home/user/trendlab/h1_{sym}.pkl').reset_index(drop=True); c=h.c.to_numpy()
        m20=pd.Series(c).rolling(20).mean().to_numpy(); m75=pd.Series(c).rolling(75).mean().to_numpy()
        cache[sym]=(h,c,m20,m75,atr7(h).to_numpy() if hasattr(atr7(h),'to_numpy') else atr7(h),m20>m75)
    h,c,m20,m75,A,up=cache[sym]
    T=h.t.to_numpy()
    for j,(li,side) in enumerate(ms):
        if side=='exit': continue
        s=1 if side=='buy' else -1; i=int(k.a)+li
        f=feats(h,c,m20,m75,A,up,i,s); f.update(w=w,sym=sym,kind=k.kind,n=sum(1 for z in ms[:j] if z[1]==side)+1,i=i,s=s)
        # nearest xlab candidate
        xs=X[(X.sym==sym)&(X.s==s)]; tt=pd.Timestamp(T[i]); dt=(pd.to_datetime(xs.t)-tt).abs()
        if len(dt): m=dt.idxmin(); f['xk']=xs.k.loc[m] if dt.loc[m]<=pd.Timedelta('3h') else 0
        rows.append(f)
    # baseline: every bar in the window, both directions
    for li in range(150,500,3):
        i=int(k.a)+li
        for s in (1,-1): b=feats(h,c,m20,m75,A,up,i,s); b.update(w=w,s=s); base.append(b)
R=pd.DataFrame(rows); B=pd.DataFrame(base)
R.to_pickle('marks_feat.pkl'); B.to_pickle('base_feat.pkl')
pd.set_option('display.width',220)
cols=['since','ok','slope75','spread','widen','d20','d75','pos20','mv','mfe','mae']
print('marks',len(R)); print(R[cols].describe().loc[['mean','25%','50%','75%']].round(2))
print('baseline (same-side as cross only)'); print(B[B.ok][cols].describe().loc[['mean','25%','50%','75%']].round(2))
print('n-th mark in window', R.n.value_counts().to_dict(), ' kind', R.kind.value_counts().to_dict())
print('nearest xlab k (0=none within 3h)', R.xk.value_counts().to_dict())
