import numpy as np
import pandas as pd
from numba import njit

@njit
def piv(high, low, atr, mult):
    out=[]; hi=0.; lo=0.; hii=0; loi=0; mode=0
    extreme=0.; extreme_i=0; initialized=False
    for i in range(len(high)):
        a=atr[i]
        if not np.isfinite(a) or a<=0: continue
        h=high[i]; l=low[i]; th=mult*a
        if mode==0:
            if not initialized:
                hi=h; lo=l; hii=i; loi=i; initialized=True; continue
            if l<=hi-th:
                out.append((1,hi,hii,i)); mode=-1; extreme=l; extreme_i=i; continue
            if h>=lo+th:
                out.append((-1,lo,loi,i)); mode=1; extreme=h; extreme_i=i; continue
            if h>hi: hi=h; hii=i
            if l<lo: lo=l; loi=i
        elif mode==1:
            if l<=extreme-th:
                out.append((1,extreme,extreme_i,i)); mode=-1; extreme=l; extreme_i=i
            elif h>extreme: extreme=h; extreme_i=i
        else:
            if h>=extreme+th:
                out.append((-1,extreme,extreme_i,i)); mode=1; extreme=h; extreme_i=i
            elif l<extreme: extreme=l; extreme_i=i
    return out

def fast(d, atr_col='atr', mult=1.5, avail_col='time'):
    raw=piv(d.high.to_numpy(),d.low.to_numpy(),d[atr_col].to_numpy(),mult)
    t=d[avail_col].to_numpy()
    return pd.DataFrame([{'kind':'H' if s==1 else 'L',
                          'price':v,'pivot_i':j,'confirm_i':i,
                          'confirm_time':t[i]} for s,v,j,i in raw])
