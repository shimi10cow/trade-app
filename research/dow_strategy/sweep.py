import sys, pandas as pd, numpy as np
B=((2003,2009),(2010,2014),(2015,2019),(2020,2024),(2025,2026))
def load(f,R,T):
    tr=pd.read_csv(f); tr['_R']=tr[R]; tr['_y']=pd.to_datetime(tr[T]).dt.year; return tr
def show(tr,nm,m):
    x=tr[m]; y=x._y; b=[x._R[(y>=a)&(y<=c)].sum() for a,c in B]
    yy=x.groupby(y)._R.sum(); eq=x._R.cumsum().to_numpy(); dd=(eq-np.maximum.accumulate(np.r_[0,eq])[1:]).min() if len(eq) else 0
    w=x._R>0; pf=x._R[w].sum()/max(1e-9,-x._R[~w].sum())
    print(f"{nm:34s} n={int(m.sum()):4d} {x._R.sum():+6.1f}R PF{pf:.2f} DD{dd:6.1f} 負け年{(yy<0).sum():2d}/{len(yy)} | "+' '.join(f'{v:+5.1f}' for v in b)+('  ★' if min(b)>0 else ''))
