"""M15 SIMPLE STRATEGY v2026-09-26 - Extreme Switch + Retracement Gate.
Causal closed-bar engine. Persistent state is stored locally as JSON.
"""
import json, math, os
from pathlib import Path

STATE_PATH=Path(os.getenv("EA_STATE_FILE",Path(__file__).with_name("m15_state.json")))

def _sma(a,n):
    out=[None]*len(a)
    for i in range(n-1,len(a)):
        w=a[i-n+1:i+1]
        if all(x is not None for x in w): out[i]=sum(w)/n
    return out

def _atr(h,l,c,n=14):
    tr=[None]*len(c)
    for i in range(len(c)):
        tr[i]=h[i]-l[i] if i==0 else max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1]))
    return _sma(tr,n)

def _stoch(h,l,c):
    raw=[None]*len(c)
    for i in range(13,len(c)):
        hi=max(h[i-13:i+1]); lo=min(l[i-13:i+1])
        raw[i]=50.0 if hi==lo else (c[i]-lo)/(hi-lo)*100.0
    k=_sma(raw,5); d=_sma(k,3)
    return k,d

def _aggregate_h1(rows):
    # MT5 epoch timestamps: group into broker/UTC clock-hour buckets.
    out=[]; bucket=[]
    for r in rows:
        hour=int(r["time"])//3600
        if bucket and int(bucket[0]["time"])//3600!=hour:
            if len(bucket)==4: out.append({"time":bucket[0]["time"],"open":bucket[0]["open"],"high":max(x["high"] for x in bucket),"low":min(x["low"] for x in bucket),"close":bucket[-1]["close"]})
            bucket=[]
        bucket.append(r)
    if len(bucket)==4: out.append({"time":bucket[0]["time"],"open":bucket[0]["open"],"high":max(x["high"] for x in bucket),"low":min(x["low"] for x in bucket),"close":bucket[-1]["close"]})
    return out

def _load():
    try:return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:return {"pairs":{}}

def _save(s):
    tmp=STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(STATE_PATH)

def _pair_state(s,pair):
    return s["pairs"].setdefault(pair,{"buy_state":0,"sell_state":0,"regime":"","p_count":0,"extreme":False,"q75":{"BUY":[],"SELL":[]},"signals":{},"last_time":0,"zz":{}})

def _pct75(xs):
    if not xs:return None
    ys=sorted(float(x) for x in xs); pos=.75*(len(ys)-1); lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    return ys[lo] if lo==hi else ys[lo]+(ys[hi]-ys[lo])*(pos-lo)

def _pip(pair):
    return 0.01 if pair.endswith("JPY") else 0.0001

def _confirmed_pivots(rows,atr):
    # Causal reversal ZigZag. A pivot is emitted only when reversal >= 1.5*current ATR.
    if not rows:return []
    trend=0; extreme=float(rows[0]["close"]); extreme_i=0; piv=[]
    for i in range(1,len(rows)):
        if atr[i] is None: continue
        hi=float(rows[i]["high"]); lo=float(rows[i]["low"]); th=1.5*float(atr[i])
        if trend>=0:
            if hi>=extreme: extreme,extreme_i=hi,i
            if extreme-lo>=th:
                piv.append(("H",extreme_i,extreme,i)); trend=-1; extreme,extreme_i=lo,i
        if trend<=0:
            if lo<=extreme: extreme,extreme_i=lo,i
            if hi-extreme>=th:
                piv.append(("L",extreme_i,extreme,i)); trend=1; extreme,extreme_i=hi,i
    return piv

def _retracement(direction,entry,piv):
    if direction=="BUY":
        for j in range(len(piv)-1,0,-1):
            if piv[j][0]=="H" and piv[j-1][0]=="L":
                lo,hi=piv[j-1][2],piv[j][2]
                if hi>lo:return (hi-entry)/(hi-lo)*100.0
    else:
        for j in range(len(piv)-1,0,-1):
            if piv[j][0]=="L" and piv[j-1][0]=="H":
                hi,lo=piv[j-1][2],piv[j][2]
                if hi>lo:return (entry-lo)/(hi-lo)*100.0
    return None

def evaluate(pair,rates,spread_price=0.0):
    rows=[{k:(int(r[k]) if k=="time" else float(r[k])) for k in ("time","open","high","low","close")} for r in rates]
    if len(rows)<2100:return None
    now=rows[-1]["time"]; state=_load(); ps=_pair_state(state,pair)
    if now<=int(ps.get("last_time",0)):return None
    c=[x["close"] for x in rows]; h=[x["high"] for x in rows]; l=[x["low"] for x in rows]
    m200=_sma(c,200); matr=_atr(h,l,c); mk,md=_stoch(h,l,c)
    h1=_aggregate_h1(rows)
    if len(h1)<505:return None
    hc=[x["close"] for x in h1]; hh=[x["high"] for x in h1]; hl=[x["low"] for x in h1]
    s20=_sma(hc,20);s75=_sma(hc,75);s200=_sma(hc,200);s480=_sma(hc,480);hatr=_atr(hh,hl,hc);hk,hd=_stoch(hh,hl,hc)
    i=len(h1)-1
    vals=(s20[i],s75[i],s20[i-1],s75[i-1],s200[i],s480[i],hatr[i],s200[i-12],s480[i-24],s480[i-12],hk[i])
    if any(x is None for x in vals):return None
    # Regime changes only on completed H1 cross.
    newreg=None
    if s20[i-1]<=s75[i-1] and s20[i]>s75[i]:newreg="BUY"
    elif s20[i-1]>=s75[i-1] and s20[i]<s75[i]:newreg="SELL"
    if newreg and newreg!=ps["regime"]:
        ps.update({"regime":newreg,"p_count":0,"extreme":False,"signals":{}})
    if ps["regime"]=="BUY" and hk[i]<20:ps["extreme"]=True
    if ps["regime"]=="SELL" and hk[i]>80:ps["extreme"]=True
    # One transition maximum per M15 bar, independently per side.
    completed=[]
    prevk,prevd=mk[-2],md[-2]; k,d=mk[-1],md[-1]
    if None not in (prevk,prevd,k,d):
        bs=ps["buy_state"]
        if bs==0 and k<20:ps["buy_state"]=1
        elif bs==1 and prevk<=prevd and k>d:ps["buy_state"]=2
        elif bs==2 and prevk<=20 and k>20:ps["buy_state"]=0;completed.append("BUY")
        ss=ps["sell_state"]
        if ss==0 and k>80:ps["sell_state"]=1
        elif ss==1 and prevk>=prevd and k<d:ps["sell_state"]=2
        elif ss==2 and prevk>=80 and k<80:ps["sell_state"]=0;completed.append("SELL")
    ps["last_time"]=now
    if not completed:_save(state);return None
    direction=completed[0]
    ps["p_count"]+=1;pnum=ps["p_count"];pattern=f"P{pnum}"
    entry=c[-1]; reasons=[]
    if ps["regime"]!=direction:reasons.append("TREND_REGIME")
    if pnum>3:reasons.append("P4_PLUS")
    if ps["extreme"]:reasons.append("H1_EXTREME_SWITCH")
    side=1 if direction=="BUY" else -1
    if side*(s200[i]-s200[i-12])<=0:reasons.append("SMA200_SLOPE")
    if side*(s480[i]-s480[i-24])<=0:reasons.append("SMA480_SLOPE")
    if side*(s200[i]-s480[i]) < -0.25*hatr[i]:reasons.append("SMA200_480_RELATION")
    strength=min(side*(s200[i]/s200[i-12]-1),side*(s480[i]/s480[i-12]-1))
    hist=ps["q75"][direction]; q75=_pct75(hist)
    if q75 is not None and strength>q75:reasons.append("Q75")
    hist.append(strength)
    # Keep persistent history bounded but long enough for live distribution.
    if len(hist)>5000:del hist[:-5000]
    piv=_confirmed_pivots(rows,matr); retr=_retracement(direction,entry,piv)
    retr_skip=False
    if retr is None: reasons.append("NO_CONFIRMED_IMPULSE")
    elif retr<0:reasons.append("RETRACEMENT_NEGATIVE");retr_skip=True
    elif retr<15 and pnum==1:reasons.append("RETRACEMENT_P1_LT15");retr_skip=True
    # P3: Retracement-skipped P1/P2 are absent. Other rejects remain non-existing/blocked and do not receive the exception.
    if pnum==3:
        prior=[ps["signals"].get("P1"),ps["signals"].get("P2")]
        existing=[x for x in prior if x and not x.get("retr_skip") and x.get("entered")]
        if len(existing)>=2 and all(float(x.get("current_r",0))<=0 for x in existing):reasons.append("P3_BOTH_NONPOSITIVE")
    pip=_pip(pair);buf=10*pip
    base=m200[-1]-buf if direction=="BUY" else m200[-1]+buf
    sl=min(base,entry-buf) if direction=="BUY" else max(base,entry+buf)
    risk=abs(entry-sl)
    if risk<=0:reasons.append("INVALID_RISK")
    elif spread_price/risk>0.10:reasons.append("SPREAD_RISK_GT10")
    structural=[x for x in reasons if x not in ()]
    candidate=not structural
    ps["signals"][pattern]={"entered":candidate,"retr_skip":retr_skip,"entry":entry,"sl":sl,"current_r":0}
    _save(state)
    return {"direction":direction,"pattern":pattern,"entry":entry,"sl":sl,"tp":None,"rule":"M15_SIMPLE_20260926",
            "strategyAllowed":candidate,"strategyReason":"OK" if candidate else ",".join(reasons),
            "retracement":retr,"q75":q75,"strength":strength,"initialRisk":risk}
