"""EA-L, EA-C (live code, default settings) and the original stochastic EA's trades on one instrument, with the environment
at each entry (causal): H4 / D1 / H1 Dow agreement, daily side, H1 MA20 distance and MA75 slope, H4/H1 impulse-line touch
within 48 h, M15 correction-line break within 8 h, M15 Dow."""
import sys, bisect, time, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from mt5_ea.live.eas import l as EL, c as EC
from env_recognition import dow_trend
from env_recognition.pivots import atr
sym=sys.argv[1]; t0=time.time()
LOGS={'XAUUSD','US500','JP225','OIL','NGAS'}
COST={'XAUUSD':2.5e-4,'US500':2e-4,'JP225':3e-4,'OIL':6e-4,'NGAS':6e-3,'GBPUSD':1.6e-4,'USDCAD':2e-4,'USDCHF':2e-4,'CADJPY':2.5e-4,'EURJPY':2e-4,'AUDJPY':1.5e-4,'CHFJPY':1.5e-4,'USDJPY':1.5e-4,'AUDUSD':1.5e-4}
m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
for z in 'ohlc':                     # gold / indices / oil / gas are already natural log in this cache
    if sym.endswith('JPY'): m[z]=m[z]/100
start='2005-06-01' if m.t.iat[0]<pd.Timestamp('2005-01-01') else str((m.t.iat[0]+pd.Timedelta(days=200)).date())
F=Frames(m,start,h_days=10000,m_days=10000); print('frames',round(time.time()-t0),flush=True)
out=[]
rl=EL.run(F); rc=EC.run(F)
for ea,r in (('L',rl),('C',rc)):
    tr=pd.DataFrame(r['trades'])
    if len(tr): out.append(pd.DataFrame(dict(ea=ea,t=pd.to_datetime(tr.t),side=tr.side,R=tr.R-(COST.get(sym,1.2e-4)-1.2e-4)/tr.risk,risk=tr.risk)))
st=pd.read_pickle(f'/home/user/trendlab/stoch/ft_{sym}.pkl')
out.append(pd.DataFrame(dict(ea='S',t=pd.to_datetime(st.time)+pd.Timedelta('15min'),side=st.side,R=st.R-COST.get(sym,1.2e-4)/st.risk,risk=st.risk,point=st.point)))
X=pd.concat(out,ignore_index=True); X=X[X.t>=pd.Timestamp(start)].reset_index(drop=True)
print('trades',X.ea.value_counts().to_dict(),round(time.time()-t0),flush=True)
# environment arrays
h4=F.h4; C4=pd.Series(pd.to_datetime(h4.t)+pd.Timedelta('4h')); A4=atr(h4); b4=F.R4['bars']; c4=h4.c.to_numpy(); sma=pd.Series(c4).rolling(1200).mean().to_numpy()
d1=h4.set_index('t').resample('1D').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index(); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
RD=dow_trend.run(d1,'D1'); CD=pd.Series(pd.to_datetime(d1.t)+pd.Timedelta('1D'))
h1=F.h1; C1=pd.Series(pd.to_datetime(h1.t)+pd.Timedelta('1h')); A1=atr(h1); m20=h1.c.rolling(20).mean().to_numpy(); m75=h1.c.rolling(75).mean().to_numpy(); c1=h1.c.to_numpy(); b1=F.R1['bars']
tl={('H4',1):[],('H4',-1):[],('H1',1):[],('H1',-1):[]}
for tf,df,R,C,A_ in (('H4',h4,F.R4,F.C4,A4),('H1',h1,F.R1,F.C1,A1)):
    for x in EL.line_touches(df,R,C,A_,tf):
        if x['kind']=='touch': tl[(tf,1 if x['d']=='up' else -1)].append(pd.Timestamp(x['t']))
for k in tl: tl[k]=sorted(tl[k])
L15,_=EC.lines(F); T15=F.T15
cb={1:sorted(T15[x[5]] for x in L15 if x[7] and x[6]=='hi'),-1:sorted(T15[x[5]] for x in L15 if x[7] and x[6]=='lo')}
CL15=T15+pd.Timedelta('15min'); b15=F.R15['bars']
def recent(lst,t,h): j=bisect.bisect_right(lst,t); return j>0 and lst[j-1]>=t-pd.Timedelta(hours=h)
rows=[]
for _,r in X.iterrows():
    t=r.t; s=int(r.side); want='up' if s==1 else 'down'
    k4=int(C4.searchsorted(t,side='right'))-1; kd=int(CD.searchsorted(t,side='right'))-1; k1=int(C1.searchsorted(t,side='right'))-1; j15=int(CL15.searchsorted(t,side='right'))-1
    if min(k4,kd,k1,j15)<80: rows.append({}); continue
    rows.append(dict(H4=float(b4[k4][0]==want),D1=float(RD['bars'][kd][0]==want),H1=float(b1[k1][0]==want),M15=float(b15[j15][0]==want),
        日足側=float(s*(c4[k4]-sma[k4])>0) if np.isfinite(sma[k4]) else np.nan,MA20距離=(c1[k1]-m20[k1])*s/A1[k1],MA75傾き=(m75[k1]-m75[k1-10])*s/A1[k1],
        MA向き=float((m20[k1]-m75[k1])*s>0),推進H4=float(recent(tl[('H4',s)],t,48)),推進H1=float(recent(tl[('H1',s)],t,48)),M15逆トレ抜け=float(recent(cb[s],t,8))))
X=pd.concat([X,pd.DataFrame(rows)],axis=1); X['sym']=sym
X.to_pickle(f'/home/user/trendlab/lc/x_{sym}.pkl'); print('done',sym,len(X),round(time.time()-t0),'s',flush=True)
