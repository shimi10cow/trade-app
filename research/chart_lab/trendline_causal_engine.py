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

def _three_candidate(a,m,b,p,close,atr,kind,tf):
    """Legacy three-point eligibility and dedup score; geometry uses only closed bars."""
    if not (a<m<b):
        return None
    gap=THREE_MAX_GAP[tf]
    if not (4<=m-a<=gap and 4<=b-m<=gap):
        return None
    sign=1 if kind=='lo' else -1
    if min(sign*(p[m]-p[a])/max(atr[m],1e-8),
           sign*(p[b]-p[m])/max(atr[b],1e-8)) < .12:
        return None
    xx=np.arange(a,b+1)
    slope=(p[b]-p[a])/(b-a)
    line=p[a]+slope*(xx-a)
    intr=line-close[xx] if kind=='lo' else close[xx]-line
    frac=float(np.mean(intr>.35*atr[xx]))
    mx=float(np.max(intr/np.maximum(atr[xx],1e-8)))
    err=abs(p[m]-(p[a]+slope*(m-a)))/max(atr[m],1e-8)
    norm=abs(p[b]-p[a])/max(np.median(atr[xx]),1e-8)
    if frac>.10 or mx>1.7 or err>.85 or not .25<=norm<=7:
        return None
    score=2*frac+.4*err+.1*max(0,norm-3)
    return dict(anchor_idx=a,end_idx=b,anchor_price=float(p[a]),
                end_price=float(p[b]),middle_idx=m,score=score)


def _select_three(candidates,tf):
    """Deterministic chronological near-duplicate suppression.

    New candidate within end-index threshold replaces a prior representative
    only when its score improves by >0.12. Otherwise reject the new candidate.
    """
    chosen={}
    for key,c in sorted(candidates.items(),
                        key=lambda kv:(kv[1]['end_idx'],kv[0])):
        near=[k for k,v in chosen.items()
              if v['kind']==c['kind'] and
              abs(v['end_idx']-c['end_idx'])<=THREE_SUPPRESS[tf]]
        if not near:
            chosen[key]=c
        else:
            best=min(near,key=lambda k:(chosen[k]['score'],k))
            if c['score']<chosen[best]['score']-.12:
                for k in near:
                    del chosen[k]
                chosen[key]=c
    return chosen


def generate_lines(df,tf,start=60,min_gap=15):
    """Return append-only create/revise/retire events with causal availability.

    Every pivot confirm/relocate recomputes affected line candidates, including
    candidates made ineligible by a relocation. Retired lines remain in the
    event log, but are absent from asof_lines() after retirement.
    """
    if len(df)<=start+1:
        return []
    atr,_=indicators(df,tf)
    close=df.c.to_numpy(float)
    prices={'lo':df.l.to_numpy(float),'hi':df.h.to_numpy(float)}
    pivots={}
    two_candidates={}
    three_candidates={}
    active={}
    out=[]
    seq=0

    def emit(now,kind,key,candidate):
        nonlocal seq
        old=active.get(key)
        if candidate is None:
            if old is None:
                return
            seq+=1
            out.append(dict(event_id=seq,action='retire',key=str(key),
                            type=key[0],tf=tf,kind=kind,
                            available_idx=now))
            del active[key]
            return
        state={k:v for k,v in candidate.items() if k!='score'}
        if old==state:
            return
        seq+=1
        action='create' if old is None else 'revise'
        out.append(dict(candidate,event_id=seq,action=action,key=str(key),
                        type=key[0],tf=tf,kind=kind,
                        available_idx=now))
        active[key]=state

    for ev in pivot_events(df,tf,start):
        now=ev['available_idx']
        pid=ev['id']
        pivots[pid]=dict(kind=ev['kind'],idx=ev['idx'])
        kind=ev['kind']
        g=[(k,v['idx']) for k,v in sorted(pivots.items())
           if v['kind']==kind]
        p=prices[kind]
        sign=1 if kind=='lo' else -1

        # Only pairs/triples involving the changed pivot can change geometry.
        for (id1,a),(id2,b) in zip(g,g[1:]):
            if pid not in (id1,id2):
                continue
            key=('two',id1,id2)
            if b-a>=min_gap and sign*(p[b]-p[a])>0:
                c=reanchor(a,b,p,kind)
                two_candidates[key]=dict(anchor_idx=c,end_idx=b,
                    anchor_price=float(p[c]),end_price=float(p[b]),
                    original_anchor_idx=a,original_gap=b-a)
            else:
                two_candidates.pop(key,None)
            emit(now,kind,key,two_candidates.get(key))

        for (id1,a),(id2,m),(id3,b) in zip(g,g[1:],g[2:]):
            if pid not in (id1,id2,id3):
                continue
            key=('three',id1,id2,id3)
            candidate=_three_candidate(a,m,b,p,close,atr,kind,tf)
            if candidate is None:
                three_candidates.pop(key,None)
            else:
                three_candidates[key]=dict(kind=kind,**candidate)

        # Re-evaluate representatives when a pivot changes, including
        # previously suppressed candidates. The old geometry is never
        # rewritten in the historical event stream.
        selected=_select_three(three_candidates,tf)
        current_three={k for k in active if k[0]=='three'}
        for key in sorted(current_three-set(selected)):
            emit(now,active[key].get('kind',kind),key,None)
        for key,c in selected.items():
            emit(now,c['kind'],key,c)
    return out


def asof_lines(events,bar_idx):
    """Active line versions observable by the close of bar_idx."""
    state={}
    for ev in events:
        if ev['available_idx']>bar_idx:
            break
        if ev['action']=='retire':
            state.pop(ev['key'],None)
        else:
            state[ev['key']]=ev
    return list(state.values())
