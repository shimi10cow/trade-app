"""Exit variants that spread the profit (SMA200 stop, entries 'newall'): partial take-profit, capped targets, H1 swing trail."""
import sys, os, numpy as np, pandas as pd
src=open('/home/user/trendlab/sx/exits.py').read()
head=src.split("def sim(")[0]
exec(head)
def sim2(i,side,entry,sl,trail='h1',half=None,cap=None,tp=None,be_after_half=False,trail_from=None):
    risk=(entry-sl)*side; on=False; part=None; t_in=T[i]
    for j in range(i+1,min(n,i+96*30)):
        if (L[j]<=sl) if side==1 else (H[j]>=sl):
            R=(sl-entry)*side/risk; return (R if part is None else 0.5*part+0.5*R), j
        fav=((H[j]-entry) if side==1 else (entry-L[j]))/risk
        if tp is not None and fav>=tp: return (tp if part is None else 0.5*part+0.5*tp), j
        if cap is not None and fav>=cap: return (cap if part is None else 0.5*part+0.5*cap), j
        if half is not None and part is None and fav>=half:
            part=half
            if be_after_half and (entry-sl)*side>0: sl=entry
        if trail is None: continue
        start=2 if trail=='m15' else (trail_from if trail_from else 1)
        if not on and (fav>=start or (trail=='m15' and (T[j]-t_in)/np.timedelta64(1,'h')>=240)): on=True
        if on:
            if trail=='h1': k=np.searchsorted(HPT,T[j],side='left')-1; TT,KK,PV=HPT,HPK,HPP
            else: k=np.searchsorted(PT,T[j],side='left')-1; TT,KK,PV=PT,PK,PP
            want='L' if side==1 else 'H'
            while k>=0 and KK[k]!=want: k-=1
            if k>=0 and (PV[k]-sl)*side>0 and (PV[k]-C[j])*side<0: sl=PV[k]
    j=min(n,i+96*30)-1; R=(C[j]-entry)*side/risk; return (R if part is None else 0.5*part+0.5*R), j
V={'4R利確':dict(trail=None,tp=4),'6R利確':dict(trail=None,tp=6),'5R利確＋3RからH1追従':dict(tp=5,trail_from=3),'5R利確＋2RからH1追従':dict(tp=5,trail_from=2),'6R利確＋3RからH1追従':dict(tp=6,trail_from=3),'2Rで半分＋残り5R':dict(trail=None,half=2,tp=5),'H1追従':dict(),'H1追従＋5Rで全部':dict(cap=5),'H1追従＋8Rで全部':dict(cap=8),'H1追従＋10Rで全部':dict(cap=10),
   '1.5Rで半分＋残りH1':dict(half=1.5),'2Rで半分＋残りH1':dict(half=2),'3Rで半分＋残りH1':dict(half=3),
   '2Rで半分＋残りH1(8Rまで)':dict(half=2,cap=8),'2Rで半分＋残り建値＋H1':dict(half=2,be_after_half=True),
   '3R利確':dict(trail=None,tp=3),'5R利確':dict(trail=None,tp=5),'M15追従(今)':dict(trail='m15')}
tr=pd.read_pickle(f'/home/user/trendlab/sx/t_{sym}_newall.pkl'); tr['time']=pd.to_datetime(tr.time); out=[]
for _,r in tr.iterrows():
    i=int(np.searchsorted(T,np.datetime64(r.time))); s=int(r.side); en=float(r.entry); sl=float(r.initial_sl)
    f=dict(sym=sym,time=r.time,side=s)
    for nm,kw in V.items():
        R,j=sim2(i,s,en,sl,**kw); f[nm]=R-COST/((en-sl)*s); f['ex|'+nm]=pd.Timestamp(T[j])
    out.append(f)
pd.DataFrame(out).to_pickle(f'/home/user/trendlab/sx/v2_{sym}.pkl'); print('done',sym,len(out),flush=True)
