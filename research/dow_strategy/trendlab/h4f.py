import pandas as pd, numpy as np
_C={}
def h4(sym):
    if sym not in _C:
        m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').set_index('time')
        b=m.resample('4h',label='left',closed='left').agg(dict(high='max',low='min',close='last')).dropna()
        pc=b.close.shift(); tr=np.maximum(b.high-b.low,np.maximum((b.high-pc).abs(),(b.low-pc).abs())); b['atr']=tr.rolling(14).mean()
        b['m20']=b.close.rolling(20).mean(); b['m75']=b.close.rolling(75).mean(); b['cl']=b.index+pd.Timedelta('4h'); _C[sym]=b
    return _C[sym]
def add(df,tcol='time'):
    out=[]
    for sym,g in df.groupby('sym'):
        b=h4(sym); k=b.cl.searchsorted(g[tcol],side='right')-1; ok=k>=10; k=np.clip(k,10,None)
        s=g.side.to_numpy()
        op=(b.m20.to_numpy()[k]-b.m75.to_numpy()[k])*s/b.atr.to_numpy()[k]; sl=(b.m75.to_numpy()[k]-b.m75.to_numpy()[k-10])*s/b.atr.to_numpy()[k]
        out.append(pd.DataFrame({'H4開き':np.where(ok,op,np.nan),'H4MA75傾き':np.where(ok,sl,np.nan)},index=g.index))
    return df.join(pd.concat(out))
