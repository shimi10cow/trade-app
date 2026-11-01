import numpy as np, pandas as pd, sys
sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr as atr7
R=pd.read_pickle('marks_feat.pkl'); K=pd.read_pickle('key.pkl').set_index('id')
cache={}
def g(sym):
    if sym not in cache:
        h=pd.read_pickle(f'/home/user/trendlab/h1_{sym}.pkl').reset_index(drop=True); cache[sym]=(h,h.c.rolling(20).mean().to_numpy(),np.asarray(atr7(h)))
    return cache[sym]
out=[]
for _,r in R.iterrows():
    h,m20,A=g(r.sym); i=int(r.i); s=r.s; o,hi,lo,c=(h[z].to_numpy() for z in 'ohlc')
    ext=(hi[i-20:i+1].max() if s==1 else lo[i-20:i+1].min()); exi=i-20+int(np.argmax(hi[i-20:i+1]) if s==1 else np.argmin(lo[i-20:i+1]))
    pbx=(lo[i-5:i+1].min() if s==1 else hi[i-5:i+1].max())
    out.append(dict(ret=(ext-c[i])*s/A[i], pbdepth=(ext-pbx)*s/A[i], pb_m20=(pbx-m20[i])*s/A[i], since_ext=i-exi,
        turn=((c[i]>hi[i-1]) if s==1 else (c[i]<lo[i-1])), bull=((c[i]>o[i]) if s==1 else (c[i]<o[i])),
        lowbar=int(np.argmin(lo[i-5:i+1]) if s==1 else np.argmax(hi[i-5:i+1]))-5))
O=pd.concat([R.reset_index(drop=True),pd.DataFrame(out)],axis=1)
pd.set_option('display.width',220)
print(O[['ret','pbdepth','pb_m20','since_ext','lowbar']].describe().loc[['mean','25%','50%','75%']].round(2))
print('turn',O.turn.mean().round(2),'bull',O.bull.mean().round(2),'ok(cross dir)',O.ok.mean().round(2))
print('pb low touched MA20 (pb_m20<=0.25)',(O.pb_m20<=0.25).mean().round(2))
print(O.groupby('n')[['since','spread','slope75','pbdepth','pb_m20','mfe']].median().round(2))
O.to_pickle('marks_feat2.pkl')
