"""H1 entry strategy (closed candles only).

Signal engine for the H1 branch. H1 bars are built from four closed M15 bars.
Execution/position management remains in main.py and the shared M15 causal exit engine.
"""
import json, math, os
from pathlib import Path

STATE_PATH=Path(os.getenv("EA_H1_STATE_FILE",Path(__file__).with_name("h1_state.json")))

def sma(a,n):
    out=[None]*len(a); total=0.0
    for i,x in enumerate(a):
        total+=x
        if i>=n: total-=a[i-n]
        if i>=n-1: out[i]=total/n
    return out

def nullable_sma(a,n):
    out=[None]*len(a)
    for i in range(n-1,len(a)):
        w=a[i-n+1:i+1]
        if all(x is not None for x in w):out[i]=sum(w)/n
    return out

def atr(h,l,c,n=14):
    tr=[]
    for i in range(len(c)):
        tr.append(h[i]-l[i] if i==0 else max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])))
    return sma(tr,n)

def stoch(h,l,c):
    raw=[None]*len(c)
    for i in range(13,len(c)):
        hi=max(h[i-13:i+1]);lo=min(l[i-13:i+1])
        raw[i]=50.0 if hi==lo else (c[i]-lo)/(hi-lo)*100.0
    k=nullable_sma(raw,5)
    return k,nullable_sma(k,3)

def aggregate_h1(rows):
    out=[];bucket=[]
    for r in rows:
        key=int(r["time"])//3600
        if bucket and int(bucket[0]["time"])//3600!=key:
            if len(bucket)==4:
                out.append({"time":int(bucket[0]["time"]),"open":float(bucket[0]["open"]),"high":max(float(x["high"]) for x in bucket),"low":min(float(x["low"]) for x in bucket),"close":float(bucket[-1]["close"])})
            bucket=[]
        bucket.append(r)
    if len(bucket)==4:
        out.append({"time":int(bucket[0]["time"]),"open":float(bucket[0]["open"]),"high":max(float(x["high"]) for x in bucket),"low":min(float(x["low"]) for x in bucket),"close":float(bucket[-1]["close"])})
    return out

def load_state():
    try:return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:return {"pairs":{}}

def save_state(s):
    STATE_PATH.parent.mkdir(parents=True,exist_ok=True)
    with STATE_PATH.open("w",encoding="utf-8") as fh:
        json.dump(s,fh,ensure_ascii=False,indent=2);fh.flush();os.fsync(fh.fileno())

def pair_state(s,pair):
    return s["pairs"].setdefault(pair,{"buy_state":0,"sell_state":0,"buy_start":None,"sell_start":None,"regime":"","p_count":0,"q75":{"BUY":[],"SELL":[]},"signals":{},"last_h1_time":0})

def register_execution(pair,pattern,direction,entry,sl,entry_time,spread_price=0.0,ticket=None,deal=None):
    state=load_state();ps=pair_state(state,pair)
    sig=ps.setdefault("signals",{}).get(pattern)
    if not sig or sig.get("direction")!=direction:raise RuntimeError(f"{pair} {pattern}: H1 signal not found for execution")
    sig.update({"entered":True,"entry":float(entry),"sl":float(sl),"entry_time":int(entry_time),"ticket":ticket,"deal":deal,"spread_price":float(spread_price or 0)})
    save_state(state);return f"H1LIVE:{int(entry_time)}:{pattern}:{direction}"

def percentile75(xs):
    if not xs:return None
    y=sorted(float(x) for x in xs);p=.75*(len(y)-1);a=int(math.floor(p));b=int(math.ceil(p))
    return y[a] if a==b else y[a]+(y[b]-y[a])*(p-a)

def pip_size(pair):
    if pair=="XAUUSD":return 1.0
    return .01 if pair.endswith("JPY") else .0001

def evaluate(pair,m15_rates,spread_price=0.0,_state=None,_save=True):
    rows=[{k:(int(r[k]) if k=="time" else float(r[k])) for k in ("time","open","high","low","close")} for r in m15_rates]
    if not rows or ((int(rows[-1]["time"])%3600)//60)!=45:return None
    h1=aggregate_h1(rows)
    if len(h1)<505:return None
    c=[x["close"] for x in h1];h=[x["high"] for x in h1];l=[x["low"] for x in h1]
    s20=sma(c,20);s75=sma(c,75);s200=sma(c,200);s480=sma(c,480);ha=atr(h,l,c);k,d=stoch(h,l,c)
    i=len(h1)-1; now=int(h1[i]["time"])
    state=_state if _state is not None else load_state();ps=pair_state(state,pair)
    if now<=int(ps.get("last_h1_time",0)):return None
    vals=(s20[i],s75[i],s20[i-1],s75[i-1],s200[i],s200[i-12],s480[i],s480[i-12],s480[i-24],ha[i],k[i],d[i])
    if any(x is None for x in vals):return None

    newreg=None
    if s20[i-1]<=s75[i-1] and s20[i]>s75[i]:newreg="BUY"
    elif s20[i-1]>=s75[i-1] and s20[i]<s75[i]:newreg="SELL"
    if newreg and newreg!=ps["regime"]:ps.update({"regime":newreg,"p_count":0,"signals":{}})

    completed=[]
    pk,pd=k[i-1],d[i-1]
    # State transitions are deliberately independent, and cross + 20/80 exit may finish on one H1 bar.
    bs=ps["buy_state"]
    if bs==0 and k[i]<20:ps["buy_state"]=1;ps["buy_start"]=now
    if ps["buy_state"]==1 and pk<=pd and k[i]>d[i]:ps["buy_state"]=2
    if ps["buy_state"]==2 and pk<=20 and k[i]>20:
        start=ps.get("buy_start");ps["buy_state"]=0;ps["buy_start"]=None;completed.append(("BUY",start))
    ss=ps["sell_state"]
    if ss==0 and k[i]>80:ps["sell_state"]=1;ps["sell_start"]=now
    if ps["sell_state"]==1 and pk>=pd and k[i]<d[i]:ps["sell_state"]=2
    if ps["sell_state"]==2 and pk>=80 and k[i]<80:
        start=ps.get("sell_start");ps["sell_state"]=0;ps["sell_start"]=None;completed.append(("SELL",start))
    ps["last_h1_time"]=now
    if not completed:
        if _save:save_state(state)
        return None

    direction,start=completed[0];ps["p_count"]+=1;pnum=ps["p_count"];pattern=f"W{pnum}";side=1 if direction=="BUY" else -1
    reasons=[]
    if ps["regime"]!=direction:reasons.append("TREND_REGIME")
    if pnum>1:reasons.append("W2_PLUS")
    if side*(s200[i]-s200[i-12])<=0:reasons.append("SMA200_SLOPE")
    if side*(s480[i]-s480[i-24])<=0:reasons.append("SMA480_SLOPE")
    if side*(s200[i]-s480[i])<-.25*ha[i]:reasons.append("SMA200_480_RELATION")

    strength=min(side*(s200[i]/s200[i-12]-1),side*(s480[i]/s480[i-24]-1))
    hist=ps["q75"][direction];q75=percentile75(hist)
    if q75 is not None and strength>q75:reasons.append("Q75")
    hist.append(strength)
    if len(hist)>10000:del hist[:-10000]

    # Wrong-side filter: reject only when both distance and continuous duration conditions hold.
    wrong_bars=0
    for j in range(i,-1,-1):
        if s200[j] is None:break
        wrong=(c[j]<s200[j]) if direction=="BUY" else (c[j]>s200[j])
        if not wrong:break
        wrong_bars+=1
    wrong_distance=(s200[i]-c[i]) if direction=="BUY" else (c[i]-s200[i])
    if wrong_distance>=.5*ha[i] and wrong_bars>=6:reasons.append("SMA200_WRONG_SIDE")

    # Pullback interval is inclusive from first extreme bar through completion bar.
    start_time=now if start is None else int(start)
    start_i=next((j for j,x in enumerate(h1) if int(x["time"])==start_time),i)
    pullback=min(x["low"] for x in h1[start_i:i+1]) if direction=="BUY" else max(x["high"] for x in h1[start_i:i+1])

    # Initial SL: search H1 SMA75/H1 SMA200/M15 SMA200 directly from pullback base within 10 pips.
    mc=[x["close"] for x in rows];m200=sma(mc,200)[-1];entry=float(c[i]);p10=10*pip_size(pair);p5=5*pip_size(pair)
    mas=[float(s75[i]),float(s200[i]),float(m200)]
    if direction=="BUY":
        nearby=[x for x in mas if x<pullback and pullback-x<=p10]
        sl=min(nearby) if nearby else pullback-p5
        risk=entry-sl
    else:
        nearby=[x for x in mas if x>pullback and x-pullback<=p10]
        sl=max(nearby) if nearby else pullback+p5
        risk=sl-entry
    if risk<=0:reasons.append("INVALID_RISK")

    candidate=not reasons
    sig={"direction":direction,"pattern":pattern,"entry":entry,"sl":sl,"tp":None,"rule":"H1_STOCH_CURRENT",
         "strategyAllowed":candidate,"strategyReason":"OK" if candidate else ",".join(reasons),
         "strength":strength,"q75":q75,"initialRisk":risk,"pullbackExtreme":pullback,"wrongSideBars":wrong_bars,"h1Time":now}
    ps["signals"][pattern]=sig
    if _save:save_state(state)
    return sig
