import pandas as pd, numpy as np
S=['XAUUSD','EURUSD','USDJPY','JP225','US500']
W=pd.concat([pd.read_pickle(f'w_{s}.pkl') for s in S],ignore_index=True)
out=[]
for s in S:
    m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{s}.pkl').set_index('time')
    for tf,rule in (('h1','1h'),('h4','4h')):
        b=m.resample(rule,label='left',closed='left').agg(dict(high='max',low='min',close='last')).dropna()
        pc=b.close.shift(); tr=np.maximum(b.high-b.low,np.maximum((b.high-pc).abs(),(b.low-pc).abs())); b['atr']=tr.rolling(14).mean()
        b['m20']=b.close.rolling(20).mean(); b['m75']=b.close.rolling(75).mean(); b['up']=np.sign(b.m20-b.m75)
        b['cl']=b.index+pd.Timedelta(rule)
        if tf=='h1': H1=b
        else: H4=b
    u1=H1.up.to_numpy(); c1=np.r_[False,(u1[1:]!=u1[:-1])&(u1[1:]!=0)]; idx1=np.flatnonzero(c1)
    u4=H4.up.to_numpy(); c4=np.r_[False,(u4[1:]!=u4[:-1])&(u4[1:]!=0)]; idx4=np.flatnonzero(c4)
    g=W[W.sym==s]
    for _,r in g.iterrows():
        t=r.time; side=r.side
        k=H1.cl.searchsorted(t,side='right')-1; j=np.searchsorted(idx1,k,side='right')   # crosses up to k
        f=dict(sym=s,time=t,side=side)
        if j>=3:
            c0,cp,cpp=idx1[j-1],idx1[j-2],idx1[j-3]
            f['前のトレンドの長さ']=c0-cp          # opposite regime before the current one (H1 bars)
            f['その前の長さ']=cp-cpp
        f['H1クロス数200']=int(((idx1>k-200)&(idx1<=k)).sum())
        k4=H4.cl.searchsorted(t,side='right')-1
        f['H4同じ向き']=float(u4[k4]==side)
        j4=np.searchsorted(idx4,k4,side='right'); f['H4クロスからの本数']=k4-idx4[j4-1] if j4>0 else np.nan
        f['H4クロス数100']=int(((idx4>k4-100)&(idx4<=k4)).sum())
        f['H4開き']=(H4.m20.iat[k4]-H4.m75.iat[k4])*side/H4.atr.iat[k4]
        f['H4MA75傾き']=(H4.m75.iat[k4]-H4.m75.iat[k4-10])*side/H4.atr.iat[k4]
        out.append(f)
pd.DataFrame(out).to_pickle('xf.pkl'); print('done',len(out))
