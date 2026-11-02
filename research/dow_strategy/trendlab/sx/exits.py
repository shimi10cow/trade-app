"""Stop / exit variants on the same entries (engine 'newall'), plus the pullback's shape at entry."""
import sys, os, numpy as np, pandas as pd
sym=sys.argv[1]; os.environ['EA_M15_CACHE']=f'/home/user/trendlab/stoch/m15_{sym}.pkl'
sys.path.insert(0,'/home/user/trade-app/research/core'); sys.path.insert(0,'/home/user/trade-app/research')
import engine_m15 as EM
from env_recognition.pivots import pivot_events
COST={'EURUSD':1.2e-4,'USDJPY':1.5e-2,'XAUUSD':2.5e-4}[sym]; pip=.01 if sym.endswith('JPY') else .0001
m,h1,h4,h1p,m15p=EM.build_features(sym)
T=m.time.to_numpy(); H=m.high.to_numpy(); L=m.low.to_numpy(); C=m.close.to_numpy(); n=len(C); A15=m.atr.to_numpy()
P=m15p.sort_values('confirm_time'); PT=P.confirm_time.to_numpy(); PK=P.kind.to_numpy(); PP=P.price.to_numpy()
h1r=h1.reset_index(drop=True); Ch=h1r.avail_time.to_numpy(); a1=h1r.atr.to_numpy()
ev=pivot_events(h1r.rename(columns=dict(open='o',high='h',low='l',close='c'))[['o','h','l','c']])
HP=sorted((Ch[e['available_idx']],'L' if e['kind']=='lo' else 'H',e['price']) for e in ev if e['action']=='confirm')
HPT=np.array([x[0] for x in HP]); HPK=np.array([x[1] for x in HP]); HPP=np.array([x[2] for x in HP])
rs=h1r.regside.to_numpy()
def last_piv(TT,KK,PPv,t,kind,entry,side,minrisk):
    j=np.searchsorted(TT,t,side='left')-1        # confirmed strictly before t
    while j>=0:
        if KK[j]==kind and (entry-PPv[j])*side>minrisk: return PPv[j]
        j-=1
    return None
def sim(i,side,entry,sl,mode):
    risk=(entry-sl)*side; on=False; tp={'tp2':2,'tp3':3}.get(mode)
    t_in=T[i]
    for j in range(i+1,min(n,i+96*30)):
        if (L[j]<=sl) if side==1 else (H[j]>=sl): return (sl-entry)*side/risk, j
        fav=((H[j]-entry) if side==1 else (entry-L[j]))/risk
        if tp and fav>=tp: return tp, j
        if mode=='regime':
            k=np.searchsorted(Ch,T[j],side='right')-1
            if k>=0 and rs[k]==-side: return (C[j]-entry)*side/risk, j
            continue
        start={'zz2':2,'zz1':1,'h1sw1':1}.get(mode)
        if start is None: continue
        if not on and (fav>=start or (mode=='zz2' and (T[j]-t_in)/np.timedelta64(1,'h')>=240)): on=True
        if on:
            if mode=='h1sw1': k=np.searchsorted(HPT,T[j],side='left')-1; TT,KK,PV=HPT,HPK,HPP
            else: k=np.searchsorted(PT,T[j],side='left')-1; TT,KK,PV=PT,PK,PP
            want='L' if side==1 else 'H'
            while k>=0 and KK[k]!=want: k-=1
            if k>=0 and (PV[k]-sl)*side>0 and (PV[k]-C[j])*side<0: sl=PV[k]
    j=min(n,i+96*30)-1; return (C[j]-entry)*side/risk, j
tr=pd.read_pickle(f'/home/user/trendlab/sx/t_{sym}_newall.pkl'); tr['time']=pd.to_datetime(tr.time)
out=[]
for _,r in tr.iterrows():
    i=int(np.searchsorted(T,np.datetime64(r.time))); s=int(r.side); en=float(r.entry); t=T[i]
    minr=10*pip
    k1=np.searchsorted(Ch,t,side='right')-1; a=a1[k1]
    sls={'sma200':float(r.initial_sl)}
    p=last_piv(PT,PK,PP,t,'L' if s==1 else 'H',en,s,minr); sls['M15山谷']=None if p is None else p-s*0.2*A15[i]
    p=last_piv(HPT,HPK,HPP,t,'L' if s==1 else 'H',en,s,minr); sls['H1山谷']=None if p is None else p-s*0.2*a
    sls['ATR1.5']=en-s*1.5*a; sls['ATR3']=en-s*3*a
    f=dict(sym=sym,time=r.time,side=s,point=r.point,regime_id=r.regime_id)
    for sn,sl in sls.items():
        if sl is None or (en-sl)*s<minr: continue
        f[f'risk_{sn}']=(en-sl)*s/a
        for mode in ('zz2','zz1','tp2','tp3','regime','h1sw1'):
            R,j=sim(i,s,en,sl,mode); f[f'{sn}|{mode}']=R-COST/((en-sl)*s)
    # pullback shape (M15): impulse since the regime start, then the pullback to now
    c0=np.searchsorted(Ch,np.datetime64(h1r.avail_time.iloc[max(0,k1-200)]))   # fallback window
    reg=np.flatnonzero(rs[:k1+1]!=s); rstart=Ch[reg[-1]] if len(reg) else Ch[0]
    i0=int(np.searchsorted(T,rstart)); seg=slice(i0,i+1)
    if i-i0>4:
        hh=np.argmax(H[seg]) if s==1 else np.argmin(L[seg]); jh=i0+hh; ext=H[jh] if s==1 else L[jh]
        base=(L[i0:jh+1].min() if s==1 else H[i0:jh+1].max()) if jh>i0 else (L[i0] if s==1 else H[i0])
        pl=(L[jh:i+1].min() if s==1 else H[jh:i+1].max())
        imp=(ext-base)*s; f['押し率']=(ext-pl)*s/imp if imp>0 else np.nan; f['推進ATR']=imp/a; f['押しATR']=(ext-pl)*s/a; f['押し本数']=i-jh
    out.append(f)
pd.DataFrame(out).to_pickle(f'/home/user/trendlab/sx/e_{sym}.pkl'); print('done',sym,len(out),flush=True)
