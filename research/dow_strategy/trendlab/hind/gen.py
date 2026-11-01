import json, numpy as np, pandas as pd, sys
sys.path.insert(0,'/home/user/trendlab')
from lab import load, legs
SY=['EURUSD','GBPUSD','AUDUSD','USDCAD','USDCHF','USDJPY','EURJPY','AUDJPY','CADJPY','CHFJPY','XAUUSD','US500','JP225','OIL','NGAS']
rng=np.random.default_rng(11); out=[]; key=[]; N=520
for sym in SY:
    h,d=load(sym); h=h.reset_index(drop=True); c=h.c; m20=c.rolling(20).mean(); m75=c.rolling(75).mean()
    T=h.t.to_numpy(); L=legs(d); L=L[L.ts>='2012-01-01']
    picks=[]
    for _,r in L.sample(2,random_state=int(rng.integers(1e6))).iterrows():
        i=int(np.searchsorted(T,np.datetime64(r.ts))); picks.append(('leg',max(100,i-150)))
    picks.append(('rnd',int(rng.integers(np.searchsorted(T,np.datetime64('2012-01-01')),len(h)-N-1))))
    for kind,a in picks:
        b=a+N; px=float(c.iloc[b-1]); dg=max(0,5-int(np.floor(np.log10(abs(px))))-1); q=lambda v:[round(float(z),dg) for z in v]
        sl=h.iloc[a:b]; out.append(dict(sym=sym,d=dg,o=q(sl.o),h=q(sl.h),l=q(sl.l),c=q(sl.c),m20=q(m20.iloc[a:b]),m75=q(m75.iloc[a:b]),
            tt=[pd.Timestamp(t).strftime('%m/%d') for t in sl.t.iloc[::40]]))
        key.append(dict(sym=sym,kind=kind,a=a,t0=T[a]))
o=np.random.default_rng(5).permutation(len(out)); out=[out[i] for i in o]; key=[key[i] for i in o]
for n,(z,k) in enumerate(zip(out,key)): z['id']=k['id']=f'w{n+1:02d}'
pd.DataFrame(key).to_pickle('/home/user/trendlab/hind/key.pkl')
open('/home/user/trendlab/hind/data.js','w').write('const DATA='+json.dumps(out,separators=(',',':'))+';')
print(len(out), pd.DataFrame(key).kind.value_counts().to_dict())
