"""M15 SIMPLE STRATEGY 2026-09-26.
Extreme Switch + Retracement Gate. Closed M15 bars only.
240h activates M15 causal ZigZag trailing; it never forces an exit.
"""
import json, math, os
from pathlib import Path

STATE_PATH=Path(os.getenv("EA_STATE_FILE",Path(__file__).with_name("m15_state.json")))

def sma(a,n):
    out=[None]*len(a); total=0.0
    for i,x in enumerate(a):
        total+=x
        if i>=n: total-=a[i-n]
        if i>=n-1: out[i]=total/n
    return out

def atr(h,l,c,n=14):
    tr=[]
    for i in range(len(c)):
        tr.append(h[i]-l[i] if i==0 else max(h[i]-l[i],abs(h[i]-c[i-1]),abs(l[i]-c[i-1])))
    return sma(tr,n)

def stoch(h,l,c):
    raw=[None]*len(c)
    for i in range(13,len(c)):
        hi=max(h[i-13:i+1]); lo=min(l[i-13:i+1])
        raw[i]=50.0 if hi==lo else (c[i]-lo)/(hi-lo)*100.0
    def nullable_sma(a,n):
        out=[None]*len(a)
        for i in range(n-1,len(a)):
            w=a[i-n+1:i+1]
            if all(x is not None for x in w): out[i]=sum(w)/n
        return out
    k=nullable_sma(raw,5)
    return k,nullable_sma(k,3)

def aggregate_h1(rows):
    out=[]; bucket=[]
    for r in rows:
        key=int(r["time"])//3600
        if bucket and int(bucket[0]["time"])//3600!=key:
            if len(bucket)==4:
                out.append({"time":bucket[0]["time"],"open":bucket[0]["open"],"high":max(x["high"] for x in bucket),"low":min(x["low"] for x in bucket),"close":bucket[-1]["close"]})
            bucket=[]
        bucket.append(r)
    if len(bucket)==4:
        out.append({"time":bucket[0]["time"],"open":bucket[0]["open"],"high":max(x["high"] for x in bucket),"low":min(x["low"] for x in bucket),"close":bucket[-1]["close"]})
    return out

def load_state():
    try:return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:return {"pairs":{}}

def save_state(s):
    tmp=STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(STATE_PATH)

def pair_state(s,pair):
    return s["pairs"].setdefault(pair,{"buy_state":0,"sell_state":0,"regime":"","p_count":0,"extreme":False,"q75":{"BUY":[],"SELL":[]},"signals":{},"trades":{},"last_time":0})

def percentile75(xs):
    if not xs:return None
    y=sorted(float(x) for x in xs); p=.75*(len(y)-1); a=int(math.floor(p)); b=int(math.ceil(p))
    return y[a] if a==b else y[a]+(y[b]-y[a])*(p-a)

def pip_size(pair):
    if pair=="XAUUSD": return 1.0
    return .01 if pair.endswith("JPY") else .0001

def pivots(rows,a):
    if not rows:return []
    trend=0; extreme=float(rows[0]["close"]); ei=0; out=[]
    for i in range(1,len(rows)):
        if a[i] is None:continue
        hi=float(rows[i]["high"]); lo=float(rows[i]["low"]); th=1.5*float(a[i])
        if trend>=0:
            if hi>=extreme:extreme,ei=hi,i
            if extreme-lo>=th:
                out.append({"type":"H","index":ei,"price":extreme,"confirmed":i})
                trend=-1;extreme,ei=lo,i
                continue
        if trend<=0:
            if lo<=extreme:extreme,ei=lo,i
            if hi-extreme>=th:
                out.append({"type":"L","index":ei,"price":extreme,"confirmed":i})
                trend=1;extreme,ei=hi,i
    return out

def retracement(direction,entry,pv):
    for j in range(len(pv)-1,0,-1):
        a,b=pv[j-1],pv[j]
        if direction=="BUY" and a["type"]=="L" and b["type"]=="H":
            d=b["price"]-a["price"]
            if d>0:return (b["price"]-entry)/d*100
        if direction=="SELL" and a["type"]=="H" and b["type"]=="L":
            d=a["price"]-b["price"]
            if d>0:return (entry-b["price"])/d*100
    return None

def trade_r(t):\n    return float(t.get("current_r",t.get("final_r",0)))\n\ndef update_trade_ledger(ps,row,pv,current_index):
    now=int(row["time"]); hi=float(row["high"]); lo=float(row["low"]); close=float(row["close"])
    ps.setdefault("trades",{})
    for t in ps["trades"].values():
        if not t.get("entered"):continue
        risk=float(t["risk"]); side=t["direction"]; entry=float(t["entry"])
        if t.get("open",False):
            # SL calculated from a pivot confirmed on the previous bar becomes active now.
            if "pending_sl" in t:t["sl"]=t.pop("pending_sl")
            # 1) Check the currently active SL first.
            active_sl=float(t["sl"])
            hit=(side=="BUY" and lo<=active_sl) or (side=="SELL" and hi>=active_sl)
            if hit:
                exit_price=active_sl
                t.update({"open":False,"exit":exit_price,"final_r":((exit_price-entry)/risk if side=="BUY" else (entry-exit_price)/risk)-float(t.get("spread_r",0)),"exit_time":now})
            else:
                # 2) +2R or 240h activates trailing. 240h itself never closes the trade.
                favorable=(hi-entry)/risk if side=="BUY" else (entry-lo)/risk
                age_hours=(now-int(t["entry_time"]))/3600.0
                if favorable>=2.0 or age_hours>=240.0:t["trailing"]=True
                # 3-5) Use only pivots confirmed no later than this closed bar.
                if t.get("trailing"):
                    relevant="L" if side=="BUY" else "H"
                    usable=[p for p in pv if p["type"]==relevant and p["confirmed"]<=current_index]
                    if usable:
                        candidate=float(usable[-1]["price"])
                        if side=="BUY" and candidate>active_sl:t["pending_sl"]=candidate
                        if side=="SELL" and candidate<active_sl:t["pending_sl"]=candidate
            if t.get("open",False):
                gross=(close-entry)/risk if side=="BUY" else (entry-close)/risk\n                t["current_r"]=gross-float(t.get("spread_r",0))
        else:t["current_r"]=float(t.get("final_r",0))

def evaluate(pair,rates,spread_price=0.0):
    rows=[{k:(int(r[k]) if k=="time" else float(r[k])) for k in ("time","open","high","low","close")} for r in rates]
    if len(rows)<2100:return None
    state=load_state(); ps=pair_state(state,pair); now=rows[-1]["time"]
    if now<=int(ps.get("last_time",0)):return None
    c=[x["close"] for x in rows];h=[x["high"] for x in rows];l=[x["low"] for x in rows]
    m200=sma(c,200);ma=atr(h,l,c);mk,md=stoch(h,l,c);pv=pivots(rows,ma)
    h1=aggregate_h1(rows)
    if len(h1)<505:return None
    hc=[x["close"] for x in h1];hh=[x["high"] for x in h1];hl=[x["low"] for x in h1]
    s20=sma(hc,20);s75=sma(hc,75);s200=sma(hc,200);s480=sma(hc,480);ha=atr(hh,hl,hc);hk,_=stoch(hh,hl,hc);i=len(h1)-1
    vals=(s20[i],s75[i],s20[i-1],s75[i-1],s200[i],s480[i],ha[i],s200[i-12],s480[i-12],s480[i-24],hk[i])
    if any(x is None for x in vals):return None

    update_trade_ledger(ps,rows[-1],pv,len(rows)-1)

    newreg=None
    if s20[i-1]<=s75[i-1] and s20[i]>s75[i]:newreg="BUY"
    elif s20[i-1]>=s75[i-1] and s20[i]<s75[i]:newreg="SELL"
    if newreg and newreg!=ps["regime"]:ps.update({"regime":newreg,"p_count":0,"extreme":False,"signals":{}})
    if ps["regime"]=="BUY" and hk[i]<20:ps["extreme"]=True
    if ps["regime"]=="SELL" and hk[i]>80:ps["extreme"]=True

    completed=[]
    pk,pd,k,d=mk[-2],md[-2],mk[-1],md[-1]
    if None not in (pk,pd,k,d):
        bs=ps["buy_state"]
        if bs==0 and k<20:ps["buy_state"]=1
        elif bs==1 and pk<=pd and k>d:ps["buy_state"]=2
        elif bs==2 and pk<=20 and k>20:ps["buy_state"]=0;completed.append("BUY")
        ss=ps["sell_state"]
        if ss==0 and k>80:ps["sell_state"]=1
        elif ss==1 and pk>=pd and k<d:ps["sell_state"]=2
        elif ss==2 and pk>=80 and k<80:ps["sell_state"]=0;completed.append("SELL")
    ps["last_time"]=now
    if not completed:save_state(state);return None

    direction=completed[0];ps["p_count"]+=1;pnum=ps["p_count"];pattern=f"P{pnum}";entry=c[-1];reasons=[]
    if ps["regime"]!=direction:reasons.append("TREND_REGIME")
    if pnum>3:reasons.append("P4_PLUS")
    if ps["extreme"]:reasons.append("H1_EXTREME_SWITCH")
    side=1 if direction=="BUY" else -1
    trend_ok=True
    if side*(s200[i]-s200[i-12])<=0:reasons.append("SMA200_SLOPE");trend_ok=False
    if side*(s480[i]-s480[i-24])<=0:reasons.append("SMA480_SLOPE");trend_ok=False
    if side*(s200[i]-s480[i]) < -.25*ha[i]:reasons.append("SMA200_480_RELATION");trend_ok=False

    strength=min(side*(s200[i]/s200[i-12]-1),side*(s480[i]/s480[i-12]-1))
    q75=None
    # q75 history is Trend+Stoch qualifying history. No arbitrary live 100-signal warmup:
    # persisted/bootstrap history supplies prior values; if none exists q75 cannot reject.
    if trend_ok:
        hist=ps["q75"][direction];q75=percentile75(hist)
        if q75 is not None and strength>q75:reasons.append("Q75")
        hist.append(strength)
        if len(hist)>10000:del hist[:-10000]

    ret=retracement(direction,entry,pv);gate_skip=False
    if ret is None:reasons.append("NO_CONFIRMED_IMPULSE")
    elif ret<0:reasons.append("RETRACEMENT_NEGATIVE");gate_skip=True
    elif ret<15 and pnum==1:reasons.append("RETRACEMENT_P1_LT15");gate_skip=True

    if pnum==3:
        p1,p2=ps["signals"].get("P1"),ps["signals"].get("P2")
        prior=[p1,p2]
        # Gate skips are the only missing-position exception.
        nongate_missing=any(x is None or (not x.get("entered") and not x.get("gate_skip")) for x in prior)
        existing=[]\n        for x in prior:\n            if x and x.get("entered"):\n                tid=x.get("trade_id"); existing.append(ps["trades"].get(tid,x) if tid else x)
        if nongate_missing:reasons.append("P3_PRIOR_NON_GATE_REJECT")
        elif existing and all(trade_r(x)<=0 for x in existing):reasons.append("P3_BOTH_NONPOSITIVE")

    buf=(10.0 if pair=="XAUUSD" else 10*pip_size(pair))
    base=m200[-1]-buf if direction=="BUY" else m200[-1]+buf
    sl=min(base,entry-buf) if direction=="BUY" else max(base,entry+buf);risk=abs(entry-sl)
    if risk<=0:reasons.append("INVALID_RISK")
    elif spread_price/risk>.10:reasons.append("SPREAD_RISK_GT10")
    if sum(1 for x in ps.setdefault("trades",{}).values() if x.get("entered") and x.get("open"))>=2:reasons.append("MAX_POSITIONS")

    candidate=not reasons
    trade={"entered":candidate,"gate_skip":gate_skip,"entry":entry,"sl":sl,"risk":risk,"direction":direction,"current_r":0.0,"open":candidate,"entry_time":now,"bar_index":len(rows)-1,"trailing":False}
    ps["signals"][pattern]=trade
    if candidate:ps.setdefault("trades",{})[f"{now}:{pattern}:{direction}"]=trade
    save_state(state)
    return {"direction":direction,"pattern":pattern,"entry":entry,"sl":sl,"tp":None,"rule":"M15_SIMPLE_20260926","strategyAllowed":candidate,
            "strategyReason":"OK" if candidate else ",".join(reasons),"retracement":ret,"q75":q75,"strength":strength,"initialRisk":risk}
