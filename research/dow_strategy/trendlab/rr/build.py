"""R@EURUSD review: live-code R trades (with and without the slope gate) + entry features + exit variants."""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app'); sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app/research/core')
from mt5_ea.live.env import Env
from mt5_ea.live.eas import rt as RT, nt as NT
from env_recognition.pivots import pivot_events
import engine_m15 as EM
F=pickle.load(open('/home/user/trendlab/live_frames_EURUSD.pkl','rb'))
env=Env(F.m15_all)
r=RT.run(F,'R2c',env=env,seed=False)
tr=pd.concat([r['trades'],pd.DataFrame(r['open'])],ignore_index=True); tr['t']=pd.to_datetime(tr.t); tr=tr[tr.t>='2005-06-01'].reset_index(drop=True)
print('R trades',len(tr),tr.R.sum().round(1))
m15=F.m15_all; shape=NT.h4_shape(m15); lev=NT._levels(F)
d=m15.rename(columns=dict(t='time',o='open',h='high',l='low',c='close'))[['time','open','high','low','close']].copy()
EM.load_m15=lambda p:d.copy(); m,h1,h4,_,m15p=EM.build_features('EURUSD'); imp=NT._impulse(m,h1)
h4b=NT._bars(m15,'4h'); a4=NT._atr_mean(h4b).to_numpy(); cl4=h4b.cl.to_numpy(); H4h=h4b.h.to_numpy(); H4l=h4b.l.to_numpy()
rows=[]
for x in tr.itertuples():
    s=int(x.side); te=x.t+pd.Timedelta('15min'); c=env.ctx_at(te,s); op,sl4=shape(x.t,s); hit,m20d=lev(te,s)
    k=int(np.searchsorted(cl4,np.datetime64(x.t),side='right'))-1
    f=dict(rs=c['rs'],sh=c['sh'],sd=c['sd'],er=c['er'],d75=c['d75'],op=op,sl4=sl4,band=hit,m20d=m20d,imp=imp(x.t,s),hour=x.t.hour)
    for n in (50,100):
        hi=H4h[k-n+1:k+1].max(); lo=H4l[k-n+1:k+1].min(); p=(x.entry-lo)/(hi-lo)
        f[f'pos{n}']=p if s==1 else 1-p; f[f'w{n}']=(hi-lo)/a4[k]; f[f'hi{n}']=hi; f[f'lo{n}']=lo
    rows.append(f)
tr=pd.concat([tr,pd.DataFrame(rows)],axis=1)
# exit variants on M15
T=m.time.to_numpy(); H=m.high.to_numpy(); L=m.low.to_numpy(); C=m.close.to_numpy(); n=len(C)
h1r=h1.reset_index(drop=True); Ch=h1r.avail_time.to_numpy()
ev=pivot_events(h1r.rename(columns=dict(open='o',high='h',low='l',close='c'))[['o','h','l','c']])
HP=sorted((Ch[e['available_idx']],'L' if e['kind']=='lo' else 'H',e['price']) for e in ev if e['action']=='confirm')
HPT=np.array([a for a,_,_ in HP]); HPK=np.array([b for _,b,_ in HP]); HPP=np.array([c for _,_,c in HP])
P=m15p.sort_values('confirm_time'); PT=P.confirm_time.to_numpy(); PK=P.kind.to_numpy(); PP=P.price.to_numpy()
def sim(i,s,en,sl,mode,tgt=None):
    risk=(en-sl)*s; on=False
    for j in range(i+1,min(n,i+96*30)):
        if (L[j]<=sl) if s==1 else (H[j]>=sl): return (sl-en)*s/risk,j
        if tgt is not None and ((H[j]>=tgt) if s==1 else (L[j]<=tgt)): return (tgt-en)*s/risk,j
        fav=((H[j]-en) if s==1 else (en-L[j]))/risk
        if mode=='none': continue
        st={'h1a1':1,'m15a1':1,'h1a2':2}[mode]
        if not on and fav>=st: on=True
        if on:
            TT,KK,PV=(HPT,HPK,HPP) if mode.startswith('h1') else (PT,PK,PP)
            k=np.searchsorted(TT,T[j],side='left')-1; want='L' if s==1 else 'H'
            while k>=0 and KK[k]!=want: k-=1
            if k>=0 and (PV[k]-sl)*s>0 and (PV[k]-C[j])*s<0: sl=PV[k]
    j=min(n,i+96*30)-1; return (C[j]-en)*s/risk,j
cost=1.2e-4; out=[]
for x in tr.itertuples():
    i=int(np.searchsorted(T,np.datetime64(x.t))); s=int(x.side); en=float(x.entry); sl=float(x.sl0); risk=(en-sl)*s; f={}
    for mode in ('h1a1','m15a1','h1a2'):
        R,j=sim(i,s,en,sl,mode); f['x_'+mode]=R-cost/risk; f['xt_'+mode]=T[j]
    for nn in (50,100):
        tg=x.__getattribute__(f'hi{nn}') if s==1 else x.__getattribute__(f'lo{nn}')
        if (tg-en)*s>0:
            R,_=sim(i,s,en,sl,'none',tg); f[f'x_far{nn}']=R-cost/risk; R,_=sim(i,s,en,sl,'h1a1',tg); f[f'x_far{nn}T']=R-cost/risk
        mid=(x.__getattribute__(f'hi{nn}')+x.__getattribute__(f'lo{nn}'))/2
        f[f'x_mid{nn}']=(sim(i,s,en,sl,'none',mid)[0]-cost/risk) if (mid-en)*s>0 else np.nan
    out.append(f)
tr=pd.concat([tr,pd.DataFrame(out)],axis=1); tr['half']=np.where(tr.t<'2016-01-01',1,2)
tr.to_pickle('/home/user/trendlab/rr/r_trades.pkl'); print('saved',len(tr))
