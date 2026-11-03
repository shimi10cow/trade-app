import numpy as np, pandas as pd
COST={'US30':1.5e-4,'US500':2e-4,'US100':2e-4,'GER40':1.5e-4,'UK100':1.5e-4,'EU50':3e-4,'OIL':6e-4,'BRENT':6e-4,'NGAS':6e-3,'JP225':3e-4}
CFG={'今のM（RSI<10・2.5ATR・SMA5で決済）':(10,2.5,'ma5'),'改良（RSI<5・1.5ATR・RSI>70で決済）':(5,1.5,'r70'),'RSI<10・1.5ATR・SMA5':(10,1.5,'ma5'),'RSI<5・2.5ATR・RSI>70':(5,2.5,'r70')}
rows=[]
for s,cost in COST.items():
    D=pd.read_pickle(f'idx/d1_{s}.pkl'); D=D[D.time.dt.dayofweek<5].reset_index(drop=True)
    o,h,l,c=(np.log(D[k].to_numpy()) for k in ('open','high','low','close')); n=len(c); T=D.time
    cs=pd.Series(c); dl=cs.diff(); up=dl.clip(lower=0).ewm(alpha=0.5).mean(); dn=(-dl.clip(upper=0)).ewm(alpha=0.5).mean(); rsi=(100-100/(1+up/dn.replace(0,np.nan))).to_numpy()
    pc=np.r_[c[0],c[:-1]]; atr=pd.Series(np.maximum(h-l,np.maximum(abs(h-pc),abs(l-pc)))).rolling(14).mean().to_numpy()
    ma5=cs.rolling(5).mean().to_numpy(); ma200=cs.rolling(200).mean().to_numpy()
    sides=(1,) if s not in ('OIL','BRENT','NGAS') else (1,-1)
    for lab,(lo,k,ex) in CFG.items():
        for sd in sides:
            sig=((c-ma200)*sd>0)&((rsi<lo) if sd==1 else (rsi>100-lo))&np.isfinite(atr)
            i=0
            while i<n-1:
                if not sig[i]: i+=1; continue
                en=c[i]; st=en-sd*k*atr[i]; risk=k*atr[i]; xp=None
                for j in range(i+1,min(i+11,n)):
                    if (l[j]<=st) if sd==1 else (h[j]>=st): xp=min(st,o[j]) if sd==1 else max(st,o[j]); break
                    done=((c[j]-ma5[j])*sd>0) if ex=='ma5' else ((rsi[j]>70) if sd==1 else (rsi[j]<30))
                    if done: xp=c[j]; break
                if xp is None: xp=c[j]
                rows.append(dict(sym=s,cfg=lab,side=sd,t=T[i],exit_t=T[j]+pd.Timedelta('1D'),R=(xp-en)*sd/risk-cost/risk)); i=j+1
d=pd.DataFrame(rows); d['half']=np.where(d.t<'2019-01-01',1,2); d.to_pickle('idx/m_all.pkl')
def st(g):
    r=g.R.to_numpy(); yrs=(g.exit_t.max()-g.t.min()).days/365.25
    return pd.Series(dict(回数=len(r),年=round(len(r)/yrs,1),勝率=(r>0).mean(),前半=g[g.half==1].R.mean(),後半=g[g.half==2].R.mean(),PF=r[r>0].sum()/max(-r[r<0].sum(),1e-9),年R=r.sum()/yrs,上位5=np.sort(r)[::-1][:5].sum()/r.sum() if r.sum()>0 else np.nan))
pd.set_option('display.width',250); pd.set_option('display.max_rows',100)
print(d.groupby(['cfg','sym']).apply(st).round(2).to_string())
