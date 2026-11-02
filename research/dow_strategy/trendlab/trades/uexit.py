import sys, bisect, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from env_recognition.pivots import atr, pivot_events
X=pd.read_pickle('trades.pkl')
M={}
def m15(sym):
    if sym not in M: M[sym]=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
    return M[sym]
HOLD=960; out=[]
for _,r in X.iterrows():
    m=m15(r.sym); w=m[(m.t>=r.tb-pd.Timedelta(days=440))&(m.t<=r.tb+pd.Timedelta(days=12))].reset_index(drop=True)
    F=Frames(w,r.tb-pd.Timedelta(days=2)); T=F.T15; CL=T+pd.Timedelta('15min'); n=len(T); i=int(T.searchsorted(r.tb))
    h,l,c=F.h,F.l,F.c; s=r.s; en=r.en; sl0=r.sl; risk=abs(en-sl0); want='up' if s==1 else 'down'; t=CL[i]
    C4=pd.Series(pd.to_datetime(F.h4.t)+pd.Timedelta('4h')); A4=atr(F.h4); k4=int(C4.searchsorted(r.tb,side='right'))-1
    d1=F.h4.set_index('t').resample('1D').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index(); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
    CD=pd.Series(pd.to_datetime(d1.t)+pd.Timedelta('1D'))
    lv=[]
    for P,C_,tf in ((F.R4['pivot_events'],C4,'H4'),(pivot_events(d1),CD,'D1')):
        last={}
        for x in P:
            if C_[x['available_idx']]<=r.tb: last[x['id']]=x
        for x in last.values():
            if x['kind']==('hi' if s==1 else 'lo') and (x['price']-en)*s>=1.0*risk: lv.append(((x['price']-en)*s/risk,tf,x['price']))
    tg=min(lv) if lv else None; tgt=tg[2] if tg else None
    rev15=sorted((CL[x['idx']],x['to']) for x in F.R15['events'] if x.get('machine')=='major' and x['action']=='REVERSAL'); rt=[a for a,_ in rev15]
    def run(be=False,m15x=False,use_t=True):
        sl=sl0
        for j in range(i,min(n,i+HOLD)):
            if (l[j]<=sl) if s==1 else (h[j]>=sl): return (sl-en)*s/risk,(j-i)/4,'損切り' if sl==sl0 else '建値'
            if use_t and tgt is not None and ((h[j]>=tgt) if s==1 else (l[j]<=tgt)): return (tgt-en)*s/risk,(j-i)/4,'水平線'
            if be and sl==sl0 and ((h[j]-en) if s==1 else (en-l[j]))>=risk: sl=en
            if m15x:
                k=bisect.bisect_right(rt,CL[j])-1
                if k>=0 and rev15[k][0]>t and rev15[k][1]!=want: return (c[j]-en)*s/risk,(j-i)/4,'M15転換'
        return (c[min(n,i+HOLD)-1]-en)*s/risk,HOLD/4,'時間'
    f=dict(id=str(r.id),sym=r.sym,s=s,R=r.R,tgtR=tg[0] if tg else np.nan,tgt_tf=tg[1] if tg else '')
    for nm,kw in (('hold',{}),('be',{'be':True}),('m15',{'m15x':True,'use_t':False}),('m15t',{'m15x':True})):
        R_,hh,why=run(**kw); f[nm]=R_; f[nm+'_h']=hh; f[nm+'_why']=why
    # environment extras at entry
    b4=F.R4['bars']; rev=[x for x in F.R4['events'] if x.get('machine')=='major' and x['action']=='REVERSAL' and x['idx']<=k4]
    f['h4age']=k4-rev[-1]['idx'] if rev else np.nan
    f['h4prot']=(en-b4[k4][1])*s/A4[k4] if b4[k4][1] is not None and b4[k4][0]==want else np.nan
    c4=F.h4.c.to_numpy(); f['h4er']=abs(c4[k4]-c4[k4-30])/np.abs(np.diff(c4[k4-30:k4+1])).sum()
    f['h4mom']=(c4[k4]-c4[k4-12])*s/A4[k4]
    A1=atr(F.h1); C1=pd.Series(pd.to_datetime(F.h1.t)+pd.Timedelta('1h')); k1=int(C1.searchsorted(r.tb,side='right'))-1
    f['vol']=A1[k1]/pd.Series(A1).rolling(500,min_periods=50).mean().iat[k1]
    f['hourJ']=r.tj.hour
    out.append(f); print(r.sym,'ok',flush=True)
pd.DataFrame(out).to_pickle('uexit.pkl'); print('done')
