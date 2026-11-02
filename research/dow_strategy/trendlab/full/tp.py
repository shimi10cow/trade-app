"""Hypothesis 'many EAs, fixed ~1R target' (2026-11): every current trade's entry and initial stop, exit at a fixed k R target
(stop first on the same bar), else the stop, else close after 5 days. Live price space (USDJPY / 100, logs for indices / metals / BTC)."""
import numpy as np, pandas as pd, numba as nb, glob
exec(open('full/eval.py').read().split("# ---------- 1 filters")[0])
X=base.copy(); X=X[~((X.key.isin(['C@EURUSD','A@EURUSD']))&(X.imp>6))]; X=X[~((X.key=='T@US30')&(X.band==1))].reset_index(drop=True)
COSTS={'EURUSD':1.2e-4,'USDJPY':1.5e-4,'XAUUSD':2.5e-4,'XAGUSD':8e-4,'US30':1.5e-4,'US500':2e-4,'JP225':3e-4,'BTCUSD':8e-4}
@nb.njit(cache=True)
def run(i0,side,en,sl,tp,h,l,c,maxb):
    for j in range(i0+1,min(i0+maxb,len(c))):
        if side==1:
            if l[j]<=sl: return (sl-en)/(en-sl)*side, j
            if h[j]>=tp: return (tp-en)/(en-sl), j
        else:
            if h[j]>=sl: return -1.0, j
            if l[j]<=tp: return (en-tp)/(sl-en), j
    j=min(i0+maxb,len(c))-1; return (c[j]-en)*side/abs(en-sl), j
out=[]
for s,g in X.groupby('sym'):
    m=pd.read_pickle(f'stoch/m15_{s}.pkl')
    if s=='USDJPY':
        for z in ('high','low','close'): m[z]=m[z]/100
    T=m.time.to_numpy(); h,l,c=(m[z].to_numpy() for z in ('high','low','close'))
    for x in g.itertuples():
        i0=int(np.searchsorted(T,np.datetime64(x.t))); sd=int(x.side); risk=abs(x.entry-x.sl0); f={}
        for k in (0.5,0.75,1.0,1.5,2.0):
            R,j=run(i0,sd,x.entry,x.sl0,x.entry+sd*k*risk,h,l,c,96*5); f[f'tp{k}']=R-COSTS[s]/risk; f[f'x{k}']=T[j]
        out.append(f)
Y=pd.concat([X.reset_index(drop=True),pd.DataFrame(out)],axis=1); Y.to_pickle('full/tp.pkl')
for col,lab in [('R','今の決済')]+[(f'tp{k}',f'+{k}Rで利確') for k in (0.5,0.75,1.0,1.5,2.0)]:
    r=Y[col].to_numpy(); yr=Y.groupby(Y.t.dt.year)[col].sum(); yr=yr[(yr.index>2005)&(yr.index<2026)]
    print(f'{lab:12s} 勝率 {(r>0).mean():.0%} 平均 {r.mean():+.3f}R PF {r[r>0].sum()/-r[r<0].sum():.2f} 前半 {Y[Y.half==1][col].mean():+.3f} 後半 {Y[Y.half==2][col].mean():+.3f}  年R 中央 {yr.median():+.0f} 最小 {yr.min():+.0f} 最大 {yr.max():+.0f}（ばらつき {yr.std()/yr.mean():.2f}）')
