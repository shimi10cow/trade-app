"""Causal Dow/2-point/3-point research engine. Bar-close event timestamps, no retroactive availability."""
import numpy as np
import pandas as pd

PARAMS={'W1':(7,1.9,.15,.4),'D1':(7,1.9,-.15,.4),'H4':(7,2.0,.30,.4),'H1':(7,2.4,-.15,.25),'M15':(7,2.1,.30,.25)}
THREE_MAX_GAP={'W1':75,'D1':95,'H4':115,'H1':145,'M15':175}
THREE_SUPPRESS={'W1':45,'D1':65,'H4':85,'H1':110,'M15':130}

def indicators(df,tf):
    ap,k,boost,cut=PARAMS[tf]
    h,l,c=(df[z].to_numpy(float) for z in ('h','l','c'))
    tr=np.maximum(h-l,np.maximum(abs(h-np.roll(c,1)),abs(l-np.roll(c,1))))
    tr[0]=h[0]-l[0]
    atr=pd.Series(tr).ewm(alpha=1/ap,adjust=False).mean().to_numpy()
    noise=pd.Series(abs(np.diff(c,prepend=c[0]))).rolling(20).sum().to_numpy()
    er=np.zeros(len(c));er[20:]=abs(c[20:]-c[:-20])/np.maximum(noise[20:],1e-12)
    return atr,k*atr*np.where(er>=cut,1+boost,1)

def pivot_events(df,tf,start=60):
    """Immutable event stream; relocate is a new event, not a historical rewrite."""
    h,l,c=(df[z].to_numpy(float) for z in ('h','l','c'))
    _,th=indicators(df,tf)
    direction=0;ei=start;ep=c[start];last=-1;ps=[];events=[]
    for i in range(start+1,len(df)):
        if direction==0:
            if h[i]>c[start]+th[i]:direction,ei,ep=1,i,h[i]
            elif l[i]<c[start]-th[i]:direction,ei,ep=-1,i,l[i]
            continue
        if direction==1:
            if h[i]>=ep:ep,ei=h[i],i
            if i>ei and ep-l[i]>=th[i] and ei>last:
                p=dict(id=len(ps),kind='hi',idx=int(ei))
                ps.append(p);events.append(dict(action='confirm',available_idx=i,**p))
                last,direction,ei,ep=ei,-1,i,l[i]
        else:
            if l[i]<=ep:ep,ei=l[i],i
            if i>ei and h[i]-ep>=th[i] and ei>last:
                p=dict(id=len(ps),kind='lo',idx=int(ei))
                ps.append(p);events.append(dict(action='confirm',available_idx=i,**p))
                last,direction,ei,ep=ei,1,i,h[i]
        if ps and direction==-1 and ps[-1]['kind']=='hi' and h[i]>h[ps[-1]['idx']]:
            p=ps[-1];p['idx']=i
            events.append(dict(action='relocate',available_idx=i,**p))
            last,ei,ep=i,i,l[i]
        elif ps and direction==1 and ps[-1]['kind']=='lo' and l[i]<l[ps[-1]['idx']]:
            p=ps[-1];p['idx']=i
            events.append(dict(action='relocate',available_idx=i,**p))
            last,ei,ep=i,i,h[i]
    return events

def reanchor(a,b,p,kind):
    """Replace A→B by C→B using the outermost intervening candle wick."""
    sign=1 if kind=='lo' else -1
    for _ in range(max(0,b-a)):
        mid=np.arange(a+1,b)
        if not len(mid):break
        line=p[a]+(p[b]-p[a])*(mid-a)/(b-a)
        intr=sign*(line-p[mid]);k=int(np.argmax(intr))
        if intr[k]<=1e-10:break
        a=int(mid[k])
    return a

def generate_lines(df,tf,start=60,min_gap=15):
    """Append-only line version events, available only at observed candle close.

    Note: D1/H4 approved archived 3-point lines and the legacy near-duplicate
    suppression are NOT automatically substituted for this causal candidate log.
    """
    if len(df)<=start+1:return []
    atr,_=indicators(df,tf);close=df.c.to_numpy(float)
    prices={'lo':df.l.to_numpy(float),'hi':df.h.to_numpy(float)}
    pivots={};versions={};out=[];seq=0
    for ev in pivot_events(df,tf,start):
        now=ev['available_idx'];pid=ev['id']
        pivots[pid]=dict(kind=ev['kind'],idx=ev['idx'])
        for kind in ('lo','hi'):
            g=[(k,v['idx']) for k,v in sorted(pivots.items()) if v['kind']==kind]
            p=prices[kind];sign=1 if kind=='lo' else -1
            for (id1,a),(id2,b) in zip(g,g[1:]):
                if pid not in (id1,id2) or b-a<min_gap or sign*(p[b]-p[a])<=0:continue
                c=reanchor(a,b,p,kind)
                key=('two',id1,id2);state=(c,b,float(p[c]),float(p[b]))
                if versions.get(key)==state:continue
                action='revise' if key in versions else 'create';versions[key]=state;seq+=1
                out.append(dict(event_id=seq,action=action,key=str(key),type='two',tf=tf,kind=kind,
                    anchor_idx=c,end_idx=b,anchor_price=float(p[c]),end_price=float(p[b]),
                    available_idx=now,original_anchor_idx=a,original_gap=b-a))
            for (id1,a),(id2,m),(id3,b) in zip(g,g[1:],g[2:]):
                if pid not in (id1,id2,id3):continue
                gap=THREE_MAX_GAP[tf]
                if not (4<=m-a<=gap and 4<=b-m<=gap):continue
                if min(sign*(p[m]-p[a])/max(atr[m],1e-8),sign*(p[b]-p[m])/max(atr[b],1e-8))<.12:continue
                xx=np.arange(a,b+1);slope=(p[b]-p[a])/(b-a);line=p[a]+slope*(xx-a)
                intr=line-close[xx] if kind=='lo' else close[xx]-line
                frac=float(np.mean(intr>.35*atr[xx]))
                mx=float(np.max(intr/np.maximum(atr[xx],1e-8)))
                err=abs(p[m]-(p[a]+slope*(m-a)))/max(atr[m],1e-8)
                norm=abs(p[b]-p[a])/max(np.median(atr[xx]),1e-8)
                if frac>.10 or mx>1.7 or err>.85 or not .25<=norm<=7:continue
                key=('three',id1,id2,id3);state=(a,b,float(p[a]),float(p[b]))
                if versions.get(key)==state:continue
                action='revise' if key in versions else 'create';versions[key]=state;seq+=1
                out.append(dict(event_id=seq,action=action,key=str(key),type='three',tf=tf,kind=kind,
                    anchor_idx=a,end_idx=b,anchor_price=float(p[a]),end_price=float(p[b]),
                    available_idx=now,middle_idx=m))
    return out

def asof_lines(events,bar_idx):
    """Latest versions that existed at bar close. Invalidations are not yet emitted."""
    state={}
    for ev in events:
        if ev['available_idx']>bar_idx:break
        state[ev['key']]=ev
    return list(state.values())
