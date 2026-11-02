import sys, os, numpy as np, pandas as pd
src=open('/home/user/trendlab/sx/exits.py').read(); exec(src.split("def sim(")[0])
def sim4(i,side,entry,sl,be=None,tstop=None,regime_cut=False,lockR=None):
    risk=(entry-sl)*side; on=False; t_in=T[i]; best=0.0
    for j in range(i+1,min(n,i+96*30)):
        if (L[j]<=sl) if side==1 else (H[j]>=sl): return (sl-entry)*side/risk, j
        fav=((H[j]-entry) if side==1 else (entry-L[j]))/risk; best=max(best,fav)
        if be is not None and best>=be and (entry-sl)*side>0: sl=entry
        if lockR is not None and best>=lockR[0] and (entry+side*lockR[1]*risk-sl)*side>0: sl=entry+side*lockR[1]*risk
        hrs=(T[j]-t_in)/np.timedelta64(1,'h')
        if tstop is not None and best<tstop[1] and hrs>=tstop[0]: return (C[j]-entry)*side/risk, j
        if regime_cut and best<1:
            k=np.searchsorted(Ch,T[j],side='right')-1
            if k>=0 and rs[k]==-side: return (C[j]-entry)*side/risk, j
        if not on and fav>=1: on=True
        if on:
            k=np.searchsorted(HPT,T[j],side='left')-1
            want='L' if side==1 else 'H'
            while k>=0 and HPK[k]!=want: k-=1
            if k>=0 and (HPP[k]-sl)*side>0 and (HPP[k]-C[j])*side<0: sl=HPP[k]
    j=min(n,i+96*30)-1; return (C[j]-entry)*side/risk, j
V={'基準(H1追従)':{},'+1Rで建値':dict(be=1),'+1.5Rで建値':dict(be=1.5),'+2Rで+0.5R確保':dict(lockR=(2,0.5)),
   '24h経って+0.5R未満なら決済':dict(tstop=(24,0.5)),'48h経って+0.5R未満なら決済':dict(tstop=(48,0.5)),'12h経って+0.3R未満なら決済':dict(tstop=(12,0.3)),
   '+1R前にMAが逆クロスしたら決済':dict(regime_cut=True)}
tr=pd.read_pickle(f'/home/user/trendlab/sx/t_{sym}_newall.pkl'); tr['time']=pd.to_datetime(tr.time); out=[]
for _,r in tr.iterrows():
    i=int(np.searchsorted(T,np.datetime64(r.time))); s=int(r.side); en=float(r.entry); sl=float(r.initial_sl)
    f=dict(sym=sym,time=r.time,side=s)
    for nm,kw in V.items():
        R,j=sim4(i,s,en,sl,**kw); f[nm]=R-COST/((en-sl)*s); f['ex|'+nm]=pd.Timestamp(T[j])
    # path facts for losers
    risk=(en-sl)*s; E_=min(n,i+96*30); fav=((H[i+1:E_]-en) if s==1 else (en-L[i+1:E_]))/risk; adv=((en-L[i+1:E_]) if s==1 else (H[i+1:E_]-en))/risk
    st=np.flatnonzero(adv>=1); js=st[0] if len(st) else len(fav); f['mfe_before_stop']=fav[:js].max() if js>0 else 0; f['bars_to_stop']=js
    out.append(f)
pd.DataFrame(out).to_pickle(f'/home/user/trendlab/sx/w_{sym}.pkl'); print('done',sym,flush=True)
