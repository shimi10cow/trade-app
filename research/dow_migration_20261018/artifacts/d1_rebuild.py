import json,sys
from pathlib import Path
import pandas as pd
sys.path.insert(0,'/mnt/data/dow_handoff')
from dow_frozen_causal_v1 import calculate_events
s=Path('/mnt/data/dow_handoff/eurusd_d1_complete_protected_review.html').read_text()
series=json.JSONDecoder().raw_decode(s.split('const SERIES=',1)[1])[0]
df=pd.DataFrame([r[:5] for r in series['D1']],columns=['t','o','h','l','c']);df.t=pd.to_datetime(df.t,utc=True)
pivots,raw=calculate_events(df,'D1'); bytime={}
for e in raw:bytime.setdefault(e['known_at'],[]).append(e)
piv={};trend=None;prot=None;ext=None;break_at=None;epoch_start=0;last_hi=None;last_lo=None;rows=[];segments=[];last_event=''
def record(i,action,pid=None):
 q=piv.get(pid,{}) if pid is not None else {}
 rows.append(dict(time=df.t.iloc[i].isoformat(),action=action,trend=trend,protected_id=prot,protected_price=piv[prot]['price'] if prot is not None else None,pivot_id=pid,anchor=pd.to_datetime(q['anchor_time'],unit='ms',utc=True).isoformat() if q else None,price=q.get('price'),close=float(df.c.iloc[i])))
def move(i,pid,reason):
 global prot
 if pid==prot:return
 if segments and segments[-1]['end'] is None:segments[-1]['end']=int(df.t.iloc[i].timestamp()*1000)
 prot=pid;q=piv[pid];segments.append(dict(start=int(df.t.iloc[i].timestamp()*1000),end=None,anchor=q['anchor_time'],price=q['price'],trend=trend,reason=reason,pivot_id=pid));record(i,reason,pid)
for i,r in enumerate(df.itertuples(index=False)):
 t=int(r.t.timestamp()*1000)
 fresh=[]
 for e in bytime.get(t,[]):
  piv[e['pivot_id']]=e.copy();fresh.append(e)
  if e['kind']=='hi':last_hi=e['pivot_id']
  else:last_lo=e['pivot_id']
  record(i,'pivot_'+e['event'],e['pivot_id'])
 if trend is None:
  if last_hi is not None and last_lo is not None:
   if r.c>piv[last_hi]['price'] and piv[last_lo]['anchor_time']<t:
    trend='up';epoch_start=i;ext=(piv[last_hi]['price'],piv[last_hi]['anchor_time']);move(i,last_lo,'start_up')
   elif r.c<piv[last_lo]['price'] and piv[last_hi]['anchor_time']<t:
    trend='down';epoch_start=i;ext=(piv[last_lo]['price'],piv[last_lo]['anchor_time']);move(i,last_hi,'start_down')
  continue
 # always check reversal even on new pivot or relocation
 if (trend=='up' and r.c<piv[prot]['price']) or (trend=='down' and r.c>piv[prot]['price']):
  record(i,'REVERSAL');old=trend;trend='down' if trend=='up' else 'up'
  window=df.iloc[epoch_start:i+1];j=window.h.idxmax() if trend=='down' else window.l.idxmin(); price=float(df.h.iloc[j] if trend=='down' else df.l.iloc[j]);pid='raw_'+str(t)
  piv[pid]=dict(price=price,anchor_time=int(df.t.iloc[j].timestamp()*1000),kind='hi' if trend=='down' else 'lo',known_at=t)
  epoch_start=i;ext=(float(r.l if trend=='down' else r.h),t);move(i,pid,'reversal_initial_raw');continue
 opposite='lo' if trend=='up' else 'hi'
 # delayed formal recognition tied to an already observed breakout
 for e in fresh:
  if e['kind']==opposite and e['anchor_time']>piv[prot]['anchor_time'] and ext[1]>e['anchor_time']:
   move(i,e['pivot_id'],'late_confirmed_protection')
 # breakout of previously tracked extreme (do not use current wick to decide)
 if (trend=='up' and r.c>ext[0]) or (trend=='down' and r.c<ext[0]):
  previous_anchor=ext[1]
  eligible=[(pid,q) for pid,q in piv.items() if q['kind']==opposite and previous_anchor<q['anchor_time']<t and q['anchor_time']>piv[prot]['anchor_time'] and q.get('known_at',0)<=t]
  if eligible:move(i,max(eligible,key=lambda z:z[1]['anchor_time'])[0],'breakout_protection')
  ext=(float(r.h if trend=='up' else r.l),t);record(i,'BREAKOUT')
if segments:segments[-1]['end']=int(df.t.iloc[-1].timestamp()*1000)
Path('/mnt/data/D1_rebuild_events.csv').write_text(pd.DataFrame(rows).to_csv(index=False),encoding='utf-8-sig')
Path('/mnt/data/D1_rebuild_lines.json').write_text(json.dumps(segments,ensure_ascii=False,indent=2))
print('candles',len(df),'pivot events',len(raw),'state events',len(rows),'line segments',len(segments),'reversals',sum(x['action']=='REVERSAL' for x in rows));print('last',segments[-5:])
