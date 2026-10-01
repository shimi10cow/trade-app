"""Read-only MT5 history/feature worker used by trade_history_analysis.py.

This process NEVER sends/modifies orders. A dedicated terminal copy is initialized,
verified against the configured login/server, queried, then shut down.
"""
import json, os, sys
from datetime import datetime, timezone
import MetaTrader5 as mt5

def iso(ts):
    return datetime.fromtimestamp(float(ts), timezone.utc).isoformat() if ts else ""

def base_symbol(s):
    s=str(s or "").upper().replace("#","")
    return "XAUUSD" if s=="GOLD" else s

def connect(cfg):
    login=int(cfg["login"]); server=str(cfg["server"]); path=str(cfg.get("terminalPath") or "")
    password=os.getenv(str(cfg.get("passwordEnv") or ""),"") if cfg.get("passwordEnv") else ""
    if password:
        kw={"login":login,"server":server,"password":password}
        ok=mt5.initialize(path,**kw) if path else mt5.initialize(**kw)
    else:
        ok=mt5.initialize(path) if path else mt5.initialize()
    if not ok: raise RuntimeError(f"initialize failed: {mt5.last_error()}")
    a=mt5.account_info()
    if not a or str(a.login)!=str(login) or str(a.server)!=server:
        raise RuntimeError("account/server lock mismatch")
    return a

def history(req,a):
    start=datetime.fromisoformat(req["start"].replace("Z","+00:00"))
    end=datetime.fromisoformat(req["end"].replace("Z","+00:00"))
    deals=mt5.history_deals_get(start,end) or []
    rows=[]
    for d in deals:
        # Keep only trade deals; balance/credit/fees unrelated to a position are excluded.
        if int(getattr(d,"position_id",0) or 0)<=0: continue
        rows.append({
          "account":str(a.login),"server":str(a.server),"ticket":str(d.ticket),
          "order":str(getattr(d,"order",0) or 0),"position_id":str(d.position_id),
          "time":iso(getattr(d,"time",0)),"time_msc":int(getattr(d,"time_msc",0) or 0),
          "symbol":base_symbol(d.symbol),"broker_symbol":str(d.symbol),
          "type":int(d.type),"entry":int(d.entry),"magic":int(getattr(d,"magic",0) or 0),
          "volume":float(getattr(d,"volume",0) or 0),"price":float(getattr(d,"price",0) or 0),
          "profit":float(getattr(d,"profit",0) or 0),"commission":float(getattr(d,"commission",0) or 0),
          "swap":float(getattr(d,"swap",0) or 0),"fee":float(getattr(d,"fee",0) or 0),
          "comment":str(getattr(d,"comment","") or "")
        })
    return {"ok":True,"account":str(a.login),"server":str(a.server),"deals":rows}

def sma(vals,n):
    return sum(vals[-n:])/n if len(vals)>=n else None

def slope_pct(vals,n,lookback):
    if len(vals)<n+lookback:return None
    now=sum(vals[-n:])/n; old=sum(vals[-n-lookback:-lookback])/n
    return ((now/old)-1)*100 if old else None

def atr(rows,n=14):
    if len(rows)<n+1:return None
    trs=[]
    for i in range(1,len(rows)):
        h=float(rows[i]["high"]);l=float(rows[i]["low"]);pc=float(rows[i-1]["close"])
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    return sum(trs[-n:])/n if len(trs)>=n else None

def stoch(rows,k_period=14,slowing=5,d_period=3):
    if len(rows)<k_period+slowing+d_period:return (None,None)
    raw=[]
    for i in range(k_period-1,len(rows)):
        w=rows[i-k_period+1:i+1]; hi=max(float(x["high"]) for x in w);lo=min(float(x["low"]) for x in w)
        raw.append(50.0 if hi==lo else 100*(float(rows[i]["close"])-lo)/(hi-lo))
    ks=[sum(raw[i-slowing+1:i+1])/slowing for i in range(slowing-1,len(raw))]
    ds=[sum(ks[i-d_period+1:i+1])/d_period for i in range(d_period-1,len(ks))]
    return (ks[-1] if ks else None,ds[-1] if ds else None)

def features(req,a):
    out=[]
    for x in req.get("trades",[]):
        broker=x.get("broker_symbol") or (("GOLD#" if x["symbol"]=="XAUUSD" else x["symbol"]+"#"))
        t=datetime.fromisoformat(str(x["entry_time"]).replace("Z","+00:00"))
        rates=mt5.copy_rates_from(broker,mt5.TIMEFRAME_H1,t,650)
        if rates is None or len(rates)<30:
            out.append({"trade_id":x["trade_id"],"feature_error":"H1 rates unavailable"});continue
        rows=[{k:(int(r[k]) if k=="time" else float(r[k])) for k in ("time","open","high","low","close")} for r in rates if int(r["time"])<int(t.timestamp())]
        closes=[r["close"] for r in rows]; last=closes[-1] if closes else None
        ma20=sma(closes,20);ma75=sma(closes,75);ma200=sma(closes,200);ma480=sma(closes,480)
        k,d=stoch(rows)
        def dist(ma): return ((last/ma)-1)*100 if last is not None and ma else None
        out.append({"trade_id":x["trade_id"],"h1_close":last,"h1_ma20":ma20,"h1_ma75":ma75,
          "h1_ma200":ma200,"h1_ma480":ma480,"h1_ma20_dist_pct":dist(ma20),"h1_ma75_dist_pct":dist(ma75),
          "h1_ma200_dist_pct":dist(ma200),"h1_ma480_dist_pct":dist(ma480),
          "h1_ma200_slope12_pct":slope_pct(closes,200,12),"h1_ma480_slope24_pct":slope_pct(closes,480,24),
          "h1_atr14":atr(rows),"h1_stoch_k":k,"h1_stoch_d":d,
          "h1_ma20_gt_75":(ma20>ma75 if ma20 is not None and ma75 is not None else None),
          "h1_ma200_gt_480":(ma200>ma480 if ma200 is not None and ma480 is not None else None)})
    return {"ok":True,"account":str(a.login),"features":out}

def main():
    req=json.loads(sys.argv[1]);a=connect(req["config"])
    try:
        action=req.get("action","history")
        ans=history(req,a) if action=="history" else features(req,a) if action=="features" else {"ok":False,"error":"unknown action"}
        print(json.dumps(ans,ensure_ascii=False))
    finally: mt5.shutdown()

if __name__=="__main__":
    try: main()
    except Exception as e:
        print(json.dumps({"ok":False,"error":str(e)},ensure_ascii=False));sys.exit(1)
