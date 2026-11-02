import sys, bisect, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from env_recognition.pivots import atr
X=pd.read_pickle('trades.pkl')
LOGS={'XAUUSD','US500','JP225'}
M={}
def m15(sym):
    if sym not in M:
        m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
        M[sym]=m
    return M[sym]
HOLD=960   # 10 days of M15
out=[]
for _,r in X.iterrows():
    m=m15(r.sym); w=m[(m.t>=r.tb-pd.Timedelta(days=440))&(m.t<=r.tb+pd.Timedelta(days=12))].reset_index(drop=True)
    F=Frames(w,r.tb-pd.Timedelta(days=2))
    T=F.T15; n=len(T); i=int(T.searchsorted(r.tb)); s=r.s; en=r.en; sl0=r.sl; risk=abs(en-sl0)
    h,l,c=F.h,F.l,F.c; CL15=T+pd.Timedelta('15min')
    # causal swings: (known time, kind, price)
    P15,P15T=F.P15,F.P15T; H1P,H1PT=F.H1P,F.H1PT
    rev15=sorted((T[x['idx']]+pd.Timedelta('15min'),x['to']) for x in F.R15['events'] if x.get('machine')=='major' and x['action']=='REVERSAL')
    prov15=sorted((T[x['idx']]+pd.Timedelta('15min'),x['to']) for x in F.R15['prov_events'] if x['action'] in('REVERSAL','PROV_START'))
    h1=F.h1; C1=pd.Series(pd.to_datetime(h1.t)+pd.Timedelta('1h')); ma20=h1.c.rolling(20).mean().to_numpy(); h1c=h1.c.to_numpy()
    against='down' if s==1 else 'up'
    def run(kind,tp=None):
        sl=sl0; on=False; mfe=0
        for j in range(i,min(n,i+HOLD)):
            if (l[j]<=sl) if s==1 else (h[j]>=sl): return (sl-en)*s/risk, j, mfe
            fav=((h[j]-en) if s==1 else (en-l[j]))/risk; mfe=max(mfe,fav)
            if tp and fav>=tp: return tp, j, mfe
            if not on and fav>=1: on=True
            t=CL15[j]
            if kind in('m15trail','h1trail') and on:
                P,PT=(P15,P15T) if kind=='m15trail' else (H1P,H1PT)
                k=bisect.bisect_right(PT,t)-1
                while k>=0 and P[k][1]!=('lo' if s==1 else 'hi'): k-=1
                if k>=0:
                    ns=P[k][2]
                    if (ns-sl)*s>0 and (ns-c[j])*s<0: sl=ns
            if kind=='m15dow':
                k=bisect.bisect_right(rev15,(t,'zz'))-1
                if k>=0 and rev15[k][1]==against and rev15[k][0]>CL15[i]: return (c[j]-en)*s/risk, j, mfe
            if kind=='m15prov':
                k=bisect.bisect_right(prov15,(t,'zz'))-1
                if k>=0 and prov15[k][1]==against and prov15[k][0]>CL15[i]: return (c[j]-en)*s/risk, j, mfe
            if kind=='h1ma' and t.minute==0:
                k=int(C1.searchsorted(t,side='right'))-1
                if k>=20 and C1[k]>CL15[i] and (h1c[k]-ma20[k])*s<0: return (h1c[k]-en)*s/risk, j, mfe
        j=min(n,i+HOLD)-1; return (c[j]-en)*s/risk, j, mfe
    f=dict(id=r.id,sym=r.sym,R=r.R,flag=r.flag)
    for k,args in [('tp1',('none',1)),('tp2',('none',2)),('tp3',('none',3)),('m15trail',('m15trail',)),('h1trail',('h1trail',)),('m15dow',('m15dow',)),('m15prov',('m15prov',)),('h1ma',('h1ma',)),('hold10d',('none',))]:
        R_,j,mfe=run(*args); f[k]=R_; f[k+'_h']=(j-i)/4
    _,_,f['mfe10d']=run('none')
    # did the original stop get hit, and then go +2R anyway (stop-then-run)?
    hit=None
    for j in range(i,min(n,i+HOLD)):
        if (l[j]<=sl0) if s==1 else (h[j]>=sl0): hit=j; break
    f['stop_hit']=hit is not None
    f['run_after_stop']=bool(hit is not None and (((h[hit:min(n,i+HOLD)].max()-en)*s/risk if s==1 else (en-l[hit:min(n,i+HOLD)].min())/risk)>=2))
    a1=atr(F.h1); f['risk_atr']=risk/a1[int(C1.searchsorted(r.tb,side='right'))-1]
    out.append(f); print(r.sym,'ok',flush=True)
pd.DataFrame(out).to_pickle('exits.pkl'); print('done')
