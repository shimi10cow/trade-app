import sys, bisect, time, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from mt5_ea.live.eas import l as EL, c as EC
from env_recognition import dow_trend
from env_recognition.pivots import atr
sym=sys.argv[1]; confs=sys.argv[2].split(','); t0=time.time()
COST={'EURUSD':1.2e-4,'USDJPY':1.5e-2,'XAUUSD':2.5e-4,'XAGUSD':8e-4,'BTCUSD':8e-4,'US30':1.5e-4,'US500':2e-4,'JP225':3e-4}
m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
if sym.endswith('JPY'):
    for z in 'ohlc': m[z]=m[z]/100
F=Frames(m,'2005-01-01',h_days=10000,m_days=10000); print('frames',round(time.time()-t0),flush=True)
X=pd.concat([pd.read_pickle(f"/home/user/trendlab/sx/t_{sym}_{c}.pkl") for c in confs],ignore_index=True)
X['Rc']=X.R-COST[sym]/X.risk; X['t']=pd.to_datetime(X.time)+pd.Timedelta('15min'); X=X[X.t>='2005-06-01'].reset_index(drop=True)
h4=F.h4; C4=pd.Series(pd.to_datetime(h4.t)+pd.Timedelta('4h')); A4=atr(h4); b4=F.R4['bars']; c4=h4.c.to_numpy()
d1=h4.set_index('t').resample('1D').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index(); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
RD=dow_trend.run(d1,'D1'); CD=pd.Series(pd.to_datetime(d1.t)+pd.Timedelta('1D')); AD=atr(d1); dsm=d1.c.rolling(20).mean().to_numpy(); dc=d1.c.to_numpy()
h1=F.h1; C1=pd.Series(pd.to_datetime(h1.t)+pd.Timedelta('1h')); A1=atr(h1); A1m=pd.Series(A1).rolling(500,min_periods=50).mean().to_numpy()
c1=h1.c.to_numpy(); hi1=h1.h.to_numpy(); lo1=h1.l.to_numpy(); m20=h1.c.rolling(20).mean().to_numpy(); m75=h1.c.rolling(75).mean().to_numpy(); b1=F.R1['bars']
up=m20>m75; crs=np.r_[False,up[1:]!=up[:-1]]; lastc=np.maximum.accumulate(np.where(crs,np.arange(len(up)),0)); ad=np.r_[0,np.cumsum(np.abs(np.diff(c1)))]
rev=[x for x in F.R4['events'] if x.get('machine')=='major' and x['action']=='REVERSAL']; revk=[x['idx'] for x in rev]
sw={k:sorted((x['available_idx'],x['price']) for x in F.R4['pivot_events'] if x['action']=='confirm' and x['kind']==k) for k in ('hi','lo')}; swk={k:[a for a,_ in v] for k,v in sw.items()}
swd={k:sorted((x['available_idx'],x['price']) for x in RD['pivot_events'] if x['action']=='confirm' and x['kind']==k) for k in ('hi','lo')}; swdk={k:[a for a,_ in v] for k,v in swd.items()}
tl={}
for tf,df,R,C,A_ in (('H4',h4,F.R4,F.C4,A4),('H1',h1,F.R1,F.C1,A1)):
    for x in EL.line_touches(df,R,C,A_,tf):
        if x['kind']=='touch': tl.setdefault((tf,1 if x['d']=='up' else -1),[]).append(pd.Timestamp(x['t']))
for k in tl: tl[k]=sorted(tl[k])
L15,_=EC.lines(F); T15=F.T15
cb={1:sorted(T15[x[5]] for x in L15 if x[7] and x[6]=='hi'),-1:sorted(T15[x[5]] for x in L15 if x[7] and x[6]=='lo')}
CL15=T15+pd.Timedelta('15min'); b15=F.R15['bars']
def recent(lst,t,h): j=bisect.bisect_right(lst,t); return j>0 and lst[j-1]>=t-pd.Timedelta(hours=h)
rows=[]
for _,r in X.iterrows():
    t=r.t; s=int(r.side); want='up' if s==1 else 'down'
    k4=int(C4.searchsorted(t,side='right'))-1; kd=int(CD.searchsorted(t,side='right'))-1; k1=int(C1.searchsorted(t,side='right'))-1; j15=int(CL15.searchsorted(t,side='right'))-1
    a=A4[k4]; lv={}
    if b4[k4][0]==want and b4[k4][1] is not None: lv['砦']=b4[k4][1]
    j=bisect.bisect_right(revk,k4)-1
    if j>=0 and rev[j]['to']==want: lv['出入口']=rev[j]['broken_price']
    kk='lo' if s==1 else 'hi'; q=bisect.bisect_right(swk[kk],k4)
    for _,p in sw[kk][max(0,q-3):q]: lv.setdefault('H4山谷',p)
    q=bisect.bisect_right(swdk[kk],kd)
    for _,p in swd[kk][max(0,q-3):q]: lv.setdefault('D1山谷',p)
    lo24=lo1[k1-23:k1+1].min(); hi24=hi1[k1-23:k1+1].max()
    hits=[nm for nm,L_ in lv.items() if ((L_-0.3*a<=lo24<=L_+0.5*a and c1[k1]>L_) if s==1 else (L_+0.3*a>=hi24>=L_-0.5*a and c1[k1]<L_))]
    i0=lastc[k1]; a0=max(0,i0-150)
    rows.append(dict(H4=float(b4[k4][0]==want),D1=float(RD['bars'][kd][0]==want),H1=float(b1[k1][0]==want),M15=float(b15[j15][0]==want),
        帯=float(bool(hits)),砦=float('砦' in hits),出入口=float('出入口' in hits),H4山谷=float('H4山谷' in hits),D1山谷=float('D1山谷' in hits),
        推進H4=float(recent(tl.get(('H4',s),[]),t,48)),推進H1=float(recent(tl.get(('H1',s),[]),t,48)),M15逆トレ抜け=float(recent(cb[s],t,8)),
        MA75傾き=(m75[k1]-m75[k1-10])*s/A1[k1],MA20距離=(c1[k1]-m20[k1])*s/A1[k1],クロスから=k1-i0,クロス前効率=abs(c1[i0]-c1[a0])/max(1e-12,ad[i0]-ad[a0]),
        ボラ=A1[k1]/A1m[k1],H4効率30=abs(c4[k4]-c4[k4-30])/np.abs(np.diff(c4[k4-30:k4+1])).sum(),日足傾き=(dsm[kd]-dsm[kd-5])*s/AD[kd],
        H4砦距離=(c1[k1]-b4[k4][1])*s/a if b4[k4][1] is not None and b4[k4][0]==want else np.nan,時刻=(t+pd.Timedelta(hours=7)).hour))
X=pd.concat([X,pd.DataFrame(rows)],axis=1)
X.to_pickle(f'/home/user/trendlab/sx/f_{sym}.pkl'); print('done',sym,len(X),round(time.time()-t0),flush=True)
