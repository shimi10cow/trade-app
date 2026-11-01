import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from env_recognition import dow_trend
from env_recognition.pivots import atr
import importlib; L=importlib.import_module('mt5_ea.live.eas.l'); L.ULOOK['D1']=20
sym=sys.argv[1]; LOGS=('XAUUSD','US500','JP225','OIL','NGAS')
m=pd.read_pickle(f'm15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
if sym in LOGS:
    for z in 'ohlc': m[z]=np.log(m[z])
def rs(h,rule): return h.set_index('t').resample(rule,label='left',closed='left').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index()
h1=rs(m,'1h'); h4=rs(m,'4h'); d1=rs(m,'1D'); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
R4=dow_trend.run(h4,'H4'); RD=dow_trend.run(d1,'D1')
A4=atr(h4); AD=atr(d1); C4=h4.t+pd.Timedelta('4h'); CD=d1.t+pd.Timedelta('1D'); C1=h1.t+pd.Timedelta('1h')
A1=pd.Series(atr(h1)).rolling(500,min_periods=50).mean().to_numpy()
hi1,lo1,c1=(h1[z].to_numpy() for z in 'hlc'); n1=len(c1)
bars4=R4['bars']; barsD=RD['bars']; sma=pd.Series(h4.c).rolling(1200).mean().to_numpy()
rev=[e for e in R4['events'] if e.get('machine')=='major' and e['action']=='REVERSAL']; revk=[e['idx'] for e in rev]
P4=sorted(((e['available_idx'],e['kind'],e['price']) for e in R4['pivot_events'] if e['action']=='confirm'))
tl=[]
for tf,df,R,C,A in (('H4',h4,R4,list(C4),A4),('D1',d1,RD,list(CD),AD)):
    for e in L.line_touches(df,R,C,A,tf):
        if e['kind']=='touch' and 3<=e['n']<=4 and e['trend']==e['d'] and e['angle']>=0.03 and e['depth'] is not None and 0.3<=e['depth']<=0.85:
            tl.append((pd.Timestamp(e['t']),1 if e['d']=='up' else -1,tf))
TLT=pd.Series([x[0] for x in tl]); TLS=np.array([x[1] for x in tl]); TLF=np.array([x[2] for x in tl])
tr=pd.read_pickle(f'tr_{sym}.pkl'); out=[]
import bisect
for _,r in tr.iterrows():
    t=pd.Timestamp(r.time)+pd.Timedelta('15min'); s=int(r.side)
    k=int(C4.searchsorted(t,side='right'))-1; kd=int(CD.searchsorted(t,side='right'))-1; i=int(C1.searchsorted(t,side='right'))-1
    if k<10 or i<30: continue
    want='up' if s==1 else 'down'; a=A4[k]
    lv={}
    if bars4[k][0]==want and bars4[k][1] is not None: lv['砦']=bars4[k][1]
    j=bisect.bisect_right(revk,k)-1
    if j>=0 and rev[j]['to']==want and all(bars4[q][0]==want for q in range(rev[j]['idx'],k+1)): lv['出入口']=rev[j]['broken_price']
    sw=[p for p in P4[:bisect.bisect_right(P4,(k,'zz',0))] if p[1]==('lo' if s==1 else 'hi')][-3:]
    for q,p in enumerate(sw): lv[f'H4谷山{q}']=p[2]
    lo24=lo1[i-23:i+1].min(); hi24=hi1[i-23:i+1].max()
    hits=[name for name,L_ in lv.items() if ((L_-0.3*a<=lo24<=L_+0.5*a and c1[i]>L_) if s==1 else (L_+0.3*a>=hi24>=L_-0.5*a and c1[i]<L_))]
    f=dict(time=r.time,side=s,R=r.R,risk=r.risk,point=r.point,
           zone=float(len(hits)>0), z_fort=float('砦' in hits), z_gate=float('出入口' in hits), z_swing=float(any(h.startswith('H4谷山') for h in hits)),
           h4=float(bars4[k][0]==want), d1=float(barsD[kd][0]==want) if kd>=0 else np.nan, dside=float(s*(h4.c.iat[k]-sma[k])>0) if not np.isnan(sma[k]) else np.nan)
    w=(TLT>=t-pd.Timedelta('24h'))&(TLT<=t)&(TLS==s) if len(tl) else pd.Series([],dtype=bool)
    f['tl']=float(w.any()) if len(tl) else 0.0; f['tl_h4']=float((w&(TLF=='H4')).any()) if len(tl) else 0.0; f['tl_d1']=float((w&(TLF=='D1')).any()) if len(tl) else 0.0
    for H in (24,72,240): f[f'f{H}']=s*(c1[min(n1-1,i+H)]-c1[i])/A1[i] if i+H<n1 else np.nan
    e=min(n1,i+241); f['mfe']=((hi1[i+1:e].max()-c1[i]) if s==1 else (c1[i]-lo1[i+1:e].min()))/A1[i]; f['mae']=((c1[i]-lo1[i+1:e].min()) if s==1 else (hi1[i+1:e].max()-c1[i]))/A1[i]
    out.append(f)
pd.DataFrame(out).assign(sym=sym).to_pickle(f'ft_{sym}.pkl'); print('done',sym,len(out))
