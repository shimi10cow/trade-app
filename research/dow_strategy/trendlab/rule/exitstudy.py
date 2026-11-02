"""Exit split study (user memo 2026-11-02): hold to the H4/D1 level vs move the stop to break-even vs exit on the M15 Dow turn.
Entries = rule.py entries. Features at entry and at the first +1R."""
import sys, bisect, time, numpy as np, pandas as pd
src=open('/home/user/trendlab/rule/rule.py').read()
pre=src.split('rows=[]; last=')[0]
exec(pre)
from env_recognition.pivots import pivot_events
d1=F.h4.set_index('t').resample('1D').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index(); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
CD=pd.Series(pd.to_datetime(d1.t)+pd.Timedelta('1D'))
pD=sorted((CD[x['available_idx']],x['kind'],x['price']) for x in pivot_events(d1) if x['action']=='confirm')
p4=sorted((C4[x['available_idx']],x['kind'],x['price']) for x in F.R4['pivot_events'] if x['action']=='confirm')
rev15=sorted((CL[x['idx']],x['to']) for x in F.R15['events'] if x.get('machine')=='major' and x['action']=='REVERSAL')
rev15t=[a for a,_ in rev15]
mtr=F.R15['bars']
def target(t,s,en,risk):
    lv=[]
    for P,tf in ((p4,'H4'),(pD,'D1')):
        k=bisect.bisect_right(P,(t,'zz',0))
        for tt,kd,p in P[max(0,k-30):k]:
            if kd==('hi' if s==1 else 'lo') and (p-en)*s>=1.0*risk: lv.append(((p-en)*s/risk,tf,p))
    if not lv: return None
    return min(lv)
def run(i,s,en,sl0,tgt,be=False,m15=False):
    risk=abs(en-sl0); sl=sl0
    for j in range(i+1,min(n,i+HOLD)):
        if (l[j]<=sl) if s==1 else (h[j]>=sl): return (sl-en)*s/risk, j, 'stop' if sl==sl0 else 'be'
        if tgt is not None and ((h[j]>=tgt) if s==1 else (l[j]<=tgt)): return (tgt-en)*s/risk, j, 'target'
        if be and sl==sl0 and ((h[j]-en) if s==1 else (en-l[j]))>=risk: sl=en
        if m15:
            k=bisect.bisect_right(rev15t,CL[j])-1
            if k>=0 and rev15[k][0]>CL[i] and rev15[k][1]==('down' if s==1 else 'up'): return (c[j]-en)*s/risk, j, 'm15'
    j=min(n,i+HOLD)-1; return (c[j]-en)*s/risk, j, 'time'
rows=[]; last={1:pd.Timestamp('1900'),-1:pd.Timestamp('1900')}
for j,s in turns:
    if j<start or j>=n-2: continue
    t=CL[j]
    if t<last[s]+pd.Timedelta('24h'): continue
    k1=int(C1.searchsorted(t,side='right'))-1; k4=int(C4.searchsorted(t,side='right'))-1
    if k1<80 or k4<20: continue
    want='up' if s==1 else 'down'
    if not(b1[k1][0]==want and (m20[k1]-m75[k1])*s>0): continue
    a4=A4[k4]; lo48=l[max(0,j-47):j+1].min(); hi48=h[max(0,j-47):j+1].max()
    hit=[nm for nm,L_ in levels(k4,s) if ((L_-0.3*a4<=lo48<=L_+0.5*a4 and c[j]>L_) if s==1 else (L_+0.3*a4>=hi48>=L_-0.5*a4 and c[j]<L_))]
    if not hit: continue
    last[s]=t; en=c[j]; sl=(lo48 if s==1 else hi48)-s*0.5*A1[k1]
    if (en-sl)*s<1e-3: sl=en-s*1e-3
    risk=(en-sl)*s; tg=target(t,s,en,risk); tgt=None if tg is None else tg[2]
    cost=COST.get(sym,1.2e-4)/risk
    f=dict(sym=sym,t=t,s=s,tgtR=tg[0] if tg else np.nan,tgt_tf=tg[1] if tg else '',risk_atr=risk/A1[k1],
           h4=float(b4[k4][0]==want),ma_sl=(m75[k1]-m75[k1-10])*s/A1[k1],d20=(en-m20[k1])*s/A1[k1],hour=t.hour)
    for nm,kw in (('hold',{}),('be',{'be':True}),('m15',{'m15':True}),('m15_nt',{'m15':True})):
        R,jx,why=run(j,s,en,sl,None if nm=='m15_nt' else tgt,**kw); f[nm]=R-cost; f[nm+'_why']=why; f[nm+'_h']=(jx-j)/4
    # first +1R: time and state then
    j1=None
    for q in range(j+1,min(n,j+HOLD)):
        if (l[q]<=sl) if s==1 else (h[q]>=sl): break
        if ((h[q]-en) if s==1 else (en-l[q]))>=risk: j1=q; break
    f['reach1']=j1 is not None
    if j1 is not None:
        f['t1_h']=(j1-j)/4; k1b=int(C1.searchsorted(CL[j1],side='right'))-1
        f['m15tr1']=float(mtr[j1][0]==want); f['ext1']=(c[j1]-m20[k1b])*s/A1[k1b]
        f['h1tr1']=float(b1[k1b][0]==want)
    rows.append(f)
pd.DataFrame(rows).to_pickle(f'/home/user/trendlab/rule/x_{sym}.pkl'); print('done',sym,len(rows),flush=True)
