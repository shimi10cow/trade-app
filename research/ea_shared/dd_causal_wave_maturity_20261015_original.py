# Archived original research script, 2026-10-15. Audit before production use.
import numpy as np,pandas as pd
from pathlib import Path
D=Path('/mnt/data/ea_shared'); t=pd.read_csv(D/'DD_structure_trade_detail.csv',parse_dates=['time']); m=pd.read_pickle(D/'EURUSD2003_M15.pkl').set_index('time').sort_index()
def build(freq,k):
 b=m.resample(freq,label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna(); b['available']=b.index+pd.Timedelta(freq)
 h=b.high.to_numpy();l=b.low.to_numpy();n=len(b);events=[]
 for i in range(k,n-k):
  if h[i]>max(h[i-k:i]) and h[i]>=max(h[i+1:i+k+1]):events.append((i+k+1,1,h[i],i))
  if l[i]<min(l[i-k:i]) and l[i]<=min(l[i+1:i+k+1]):events.append((i+k+1,-1,l[i],i))
 events.sort(); confirmed=[]
 for e in events:
  if e[0]>=n:continue
  if confirmed and e[1]==confirmed[-1][1]:
   if (e[1]==1 and e[2]>confirmed[-1][2]) or (e[1]==-1 and e[2]<confirmed[-1][2]):confirmed[-1]=e
  else:confirmed.append(e)
 return b,confirmed
b4,e4=build('4h',2);b1,e1=build('1h',2)
def features(b,events,prefix):
 dates=np.array(b.index);ei=np.array([e[0] for e in events]);pos=np.searchsorted(ei,np.searchsorted(dates,t.time.to_numpy(),side='right')-1,side='right')-1
 out=[]
 for j,p in enumerate(pos):
  v=events[max(0,p-6):p+1] if p>=0 else []
  swings=[(v[z][2]-v[z-1][2],v[z][1],v[z][3]-v[z-1][3]) for z in range(1,len(v))]
  direction=int(t.side.iloc[j]);imp=[abs(s[0]) for s in swings if s[1]==direction];pull=[abs(s[0]) for s in swings if s[1]==-direction]
  last=imp[-1] if imp else np.nan;prior=imp[-2] if len(imp)>1 else np.nan;latestpull=pull[-1] if pull else np.nan
  age=(t.time.iloc[j]-dates[v[-1][0]]).total_seconds()/3600 if v else np.nan
  out.append([len(v),len(imp),age,last/prior if prior>0 else np.nan,latestpull/last if last>0 else np.nan,(v[-1][2]-v[-3][2])*direction if len(v)>=3 else np.nan])
 return pd.DataFrame(out,columns=[prefix+'_'+x for x in ['pivots','impulses','hours_since_confirmation','impulse_ratio','pullback_ratio','net_2swings']])
f=pd.concat([t,features(b4,e4,'h4'),features(b1,e1,'h1')],axis=1)
f['h1_h4_impulse_ratio']=f.h1_impulse_ratio/f.h4_impulse_ratio
f['h4_mature_weak']=(f.h4_impulse_ratio<.7)&(f.h4_pullback_ratio>.6)
f['h4_mature_weak_and_far']=f.h4_mature_weak&(f.dist480>=12)
f['h1_weak_h4_weak']=(f.h1_impulse_ratio<.7)&(f.h4_impulse_ratio<.7)
f['h4_weak_only']=f.h4_impulse_ratio<.7
f['h4_pullback_deep']=f.h4_pullback_ratio>.8
f['h4_recent_pivot']=f.h4_hours_since_confirmation<12
def stats(a):
 w=a.loc[a.R>0,'R'].sum();loss=-a.loc[a.R<0,'R'].sum();return len(a),round(a.R.sum(),3),round(w/loss,3) if loss else np.nan,round(a.R.mean(),3)
rows=[]
for name,mask in [('all',pd.Series(True,index=f.index)),('h4 impulse shrink <0.7',f.h4_weak_only),('h4 pullback/impulse >0.8',f.h4_pullback_deep),('h4 shrink and deep pullback',f.h4_mature_weak),('h4 shrink+deep+far',f.h4_mature_weak_and_far),('h1 and h4 impulse shrink',f.h1_weak_h4_weak),('h4 last pivot confirmed <12h',f.h4_recent_pivot)]:
 for group,sub in [('all',f),('DD2011_2019',f[(f.time>='2011-11-01')&(f.time<='2019-09-30')]),('other',f[~((f.time>='2011-11-01')&(f.time<='2019-09-30'))])]:
  n,r,pf,avg=stats(sub.loc[mask.reindex(sub.index).fillna(False)]);rows.append([name,group,n,r,pf,avg])
for col,bins in [('h4_impulse_ratio',[0,.5,.75,1,1.5,2,100]),('h4_pullback_ratio',[0,.3,.6,1,1.5,100]),('h4_hours_since_confirmation',[0,12,24,48,96,100000]),('h1_impulse_ratio',[0,.5,.75,1,1.5,2,100])]:
 for cat,g in f.groupby(pd.cut(f[col],bins,include_lowest=True),observed=True):
  n,r,pf,avg=stats(g);rows.append([col+' '+str(cat),'all',n,r,pf,avg])
pd.DataFrame(rows,columns=['condition','period','n','sumR','PF','avgR']).to_csv(D/'DD_causal_wave_maturity_summary.csv',index=False)
f.to_csv(D/'DD_causal_wave_maturity_trades.csv',index=False)
