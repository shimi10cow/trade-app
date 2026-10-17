"""Dow pivot engine, frozen v1 2026-10-17. Retrospective pivots may repaint."""
import numpy as np
import pandas as pd
from numba import njit

PARAMS = {'W1': (7,1.9,.15,.4), 'D1': (7,1.9,-.15,.4),
          'H4': (7,2.0,.3,.4), 'H1': (7,2.4,-.15,.25),
          'M15': (7,2.1,.3,.25)}

@njit
def detect(h,l,c,threshold,start,end,relocate=True):
    out=np.empty((end-start+1,3),np.int64)
    n=0; direction=0; ei=start; ep=c[start]; last=-1
    for i in range(start+1,end+1):
        th=threshold[i]
        if direction==0:
            if h[i]>c[start]+th:
                direction=1; ei=i; ep=h[i]
            elif l[i]<c[start]-th:
                direction=-1; ei=i; ep=l[i]
            continue
        if direction==1:
            if h[i]>=ep: ep=h[i]; ei=i
            if i>ei and ep-l[i]>=th and ei>last:
                out[n,0]=ei; out[n,1]=1; out[n,2]=i
                n+=1; last=ei; direction=-1; ei=i; ep=l[i]
        else:
            if l[i]<=ep: ep=l[i]; ei=i
            if i>ei and h[i]-ep>=th and ei>last:
                out[n,0]=ei; out[n,1]=-1; out[n,2]=i
                n+=1; last=ei; direction=1; ei=i; ep=h[i]
        if relocate and n>0 and direction==-1 and out[n-1,1]==1 and h[i]>h[out[n-1,0]]:
            out[n-1,0]=i; out[n-1,2]=i; last=i; ei=i; ep=l[i]
        elif relocate and n>0 and direction==1 and out[n-1,1]==-1 and l[i]<l[out[n-1,0]]:
            out[n-1,0]=i; out[n-1,2]=i; last=i; ei=i; ep=h[i]
    return out[:n]

def calculate(df,tf,start=60,end=None):
    """Columns t,o,h,l,c. Returns list of {'t':epoch_ms,'kind':'hi'|'lo'}."""
    ap,k,boost,cut=PARAMS[tf]
    h=df.h.to_numpy(float); l=df.l.to_numpy(float); c=df.c.to_numpy(float)
    tr=np.maximum(h-l,np.maximum(abs(h-np.roll(c,1)),abs(l-np.roll(c,1))))
    tr[0]=h[0]-l[0]
    atr=pd.Series(tr).ewm(alpha=1/ap,adjust=False).mean().to_numpy()
    noise=pd.Series(abs(np.diff(c,prepend=c[0]))).rolling(20).sum().to_numpy()
    er=np.zeros(len(c))
    er[20:]=abs(c[20:]-c[:-20])/np.maximum(noise[20:],1e-12)
    th=k*atr*np.where(er>=cut,1+boost,1)
    end=len(df)-1 if end is None else end
    if not (0<=start<end<len(df)):
        raise ValueError("Invalid start/end indices")
    p=detect(h,l,c,th,start,end)
    t=pd.to_datetime(df.t).astype('int64').to_numpy()//10**6
    return [{'t':int(t[i]),'kind':'hi' if kind==1 else 'lo'} for i,kind,_ in p]
