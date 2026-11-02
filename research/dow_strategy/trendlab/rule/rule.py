"""User-style rule (2026-11-02): H1 Dow + H1 MA20/75 same side, price came back to an H4 level (砦 / 出入口 / recent H4 swing)
within the last 12 h and held, then an M15 turn in the trade direction -> enter at that M15 close.
Stop: below the lowest low since the touch (and the level) - 0.5 ATR(H1). Exits: several, from the same entry."""
import sys, bisect, time, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from env_recognition.pivots import atr
sym=sys.argv[1]
LOGS={'XAUUSD','US500','JP225','OIL','NGAS'}
COST={'XAUUSD':2.5e-4,'US500':2e-4,'JP225':3e-4,'OIL':6e-4,'NGAS':6e-3,'GBPUSD':1.6e-4,'USDCAD':2e-4,'USDCHF':2e-4,'CADJPY':2.5e-4,'EURJPY':2e-4,'AUDJPY':1.5e-4,'CHFJPY':1.5e-4,'USDJPY':1.5e-4,'AUDUSD':1.5e-4}
m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
for z in 'ohlc':
    if sym in LOGS: m[z]=np.log(m[z])
    elif sym.endswith('JPY'): m[z]=m[z]/100
t0=time.time(); F=Frames(m,'2005-06-01' if m.t.iat[0]<pd.Timestamp('2005-01-01') else m.t.iat[0]+pd.Timedelta(days=200),h_days=10000,m_days=10000)
print('frames',round(time.time()-t0),'s',flush=True)
T=F.T15; n=len(T); CL=T+pd.Timedelta('15min'); h,l,c=F.h,F.l,F.c
h1=F.h1; C1=pd.Series(pd.to_datetime(h1.t)+pd.Timedelta('1h')); A1=atr(h1); m20=h1.c.rolling(20).mean().to_numpy(); m75=h1.c.rolling(75).mean().to_numpy()
h4=F.h4; C4=pd.Series(pd.to_datetime(h4.t)+pd.Timedelta('4h')); A4=atr(h4); b4=F.R4['bars']; b1=F.R1['bars']
rev=[x for x in F.R4['events'] if x.get('machine')=='major' and x['action']=='REVERSAL']; revk=[x['idx'] for x in rev]
sw={k:sorted((x['available_idx'],x['price']) for x in F.R4['pivot_events'] if x['action']=='confirm' and x['kind']==k) for k in ('hi','lo')}
swk={k:[a for a,_ in v] for k,v in sw.items()}
turns=[(x['idx'],1 if x['to']=='up' else -1) for x in F.R15['prov_events'] if x['action'] in('REVERSAL','PROV_START')]
P15,P15T,H1P,H1PT=F.P15,F.P15T,F.H1P,F.H1PT
start=int(T.searchsorted(F.START))
def levels(k,s):
    want='up' if s==1 else 'down'; out=[]
    if b4[k][0]==want and b4[k][1] is not None: out.append(('砦',b4[k][1]))
    j=bisect.bisect_right(revk,k)-1
    if j>=0 and rev[j]['to']==want and all(b4[q][0]==want for q in range(rev[j]['idx'],k+1)): out.append(('出入口',rev[j]['broken_price']))
    kk='lo' if s==1 else 'hi'; q=bisect.bisect_right(swk[kk],k)
    for _,p in sw[kk][max(0,q-3):q]: out.append(('山谷',p))
    return out
HOLD=960
def sim(i,s,en,sl0,kind,tp=None):
    risk=abs(en-sl0); sl=sl0; on=False; half=None
    for j in range(i+1,min(n,i+HOLD)):
        if (l[j]<=sl) if s==1 else (h[j]>=sl):
            R=(sl-en)*s/risk; return (0.5*half+0.5*R if half is not None else R), j
        fav=((h[j]-en) if s==1 else (en-l[j]))/risk
        if tp and fav>=tp and kind=='tp': return tp, j
        if kind=='half' and half is None and fav>=1: half=1.0; sl=en
        if not on and fav>=1: on=True
        if kind in('m15trail','half','h1trail') and on:
            P,PT=(H1P,H1PT) if kind=='h1trail' else (P15,P15T)
            k=bisect.bisect_right(PT,CL[j])-1
            while k>=0 and P[k][1]!=('lo' if s==1 else 'hi'): k-=1
            if k>=0 and (P[k][2]-sl)*s>0 and (P[k][2]-c[j])*s<0: sl=P[k][2]
    j=min(n,i+HOLD)-1; R=(c[j]-en)*s/risk; return (0.5*half+0.5*R if half is not None else R), j
rows=[]; last={1:pd.Timestamp('1900'),-1:pd.Timestamp('1900')}
for j,s in turns:
    if j<start or j>=n-2: continue
    t=CL[j]
    if t<last[s]+pd.Timedelta('24h'): continue
    k1=int(C1.searchsorted(t,side='right'))-1; k4=int(C4.searchsorted(t,side='right'))-1
    if k1<80 or k4<20: continue
    want='up' if s==1 else 'down'
    h1dow=b1[k1][0]==want; h1ma=(m20[k1]-m75[k1])*s>0
    a4=A4[k4]; lo48=l[max(0,j-47):j+1].min(); hi48=h[max(0,j-47):j+1].max()
    hit=[nm for nm,L_ in levels(k4,s) if ((L_-0.3*a4<=lo48<=L_+0.5*a4 and c[j]>L_) if s==1 else (L_+0.3*a4>=hi48>=L_-0.5*a4 and c[j]<L_))]
    lvl=min([L_ for nm,L_ in levels(k4,s)] if s==1 else [L_ for nm,L_ in levels(k4,s)],default=None)
    ext=lo48 if s==1 else hi48
    sl=ext-s*0.5*A1[k1]
    en=c[j]
    if (en-sl)*s<1e-3: sl=en-s*1e-3
    f=dict(sym=sym,t=t,s=s,h1dow=h1dow,h1ma=h1ma,zone=','.join(hit),risk_atr=(en-sl)*s/A1[k1])
    cost=COST.get(sym,1.2e-4)/((en-sl)*s)
    if h1dow and h1ma and hit:
        last[s]=t
        for kind,tp in (('tp',1),('tp',1.5),('tp',2),('tp',3),('m15trail',None),('h1trail',None),('half',None)):
            R,jx=sim(j,s,en,sl,kind,tp); key=kind+(str(tp) if tp else ''); f[key]=R-cost; f[key+'_h']=(jx-j)/4
        rows.append(f)
pd.DataFrame(rows).to_pickle(f'/home/user/trendlab/rule/r_{sym}.pkl'); print('done',sym,len(rows),round(time.time()-t0),'s')
