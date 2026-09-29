"""Historical EA signal replay requested by the Trade Tracker app.

Read-only toward MT5: it never sends/modifies orders and never sends Telegram.
It replays closed M15 bars in isolated temporary strategy state files and writes
only strategy-valid signals to EA_Signals through the existing GAS endpoint.
"""
import argparse,json,os,tempfile
from datetime import datetime,timezone,timedelta
from pathlib import Path

def _dt(s):
    x=datetime.fromisoformat(str(s).replace("Z","+00:00"))
    if x.tzinfo is None:x=x.replace(tzinfo=timezone(timedelta(hours=9)))
    return x.astimezone(timezone.utc)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--pair",required=True);ap.add_argument("--start",required=True);ap.add_argument("--end",required=True)
    ap.add_argument("--m15",action="store_true");ap.add_argument("--h1",action="store_true");ap.add_argument("--gas-url",default=os.getenv("EA_GAS_URL",""))
    a=ap.parse_args()
    if not a.m15 and not a.h1:raise SystemExit("Select M15 and/or H1")
    if not a.gas_url:raise SystemExit("EA_GAS_URL is required")
    start,end=_dt(a.start),_dt(a.end)
    if end<start:raise SystemExit("End must be after start")
    import MetaTrader5 as mt5,requests
    if not mt5.initialize():raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
      from main import resolve_symbol
      symbol=resolve_symbol(a.pair)
      if not symbol:raise SystemExit("Broker symbol not found")
      # 35 calendar days safely covers H1 SMA480 across weekends plus margin. Replay through now so
      # signals opened inside the requested interval can reach their causal exit.
      warm=start-timedelta(days=35); now=datetime.now(timezone.utc)
      rates=mt5.copy_rates_range(symbol,mt5.TIMEFRAME_M15,warm,now)
      if rates is None or len(rates)<2100:raise SystemExit("Not enough M15 history")
      rows=list(rates); spread=0.0
      tick=mt5.symbol_info_tick(symbol)
      if tick and tick.ask and tick.bid:spread=max(0.0,float(tick.ask)-float(tick.bid))
      with tempfile.TemporaryDirectory(prefix="ea_replay_") as td:
        os.environ["EA_STATE_FILE"]=str(Path(td)/"m15.json");os.environ["EA_H1_STATE_FILE"]=str(Path(td)/"h1.json")
        import importlib,m15_strategy,h1_strategy
        importlib.reload(m15_strategy);importlib.reload(h1_strategy)
        ms={"pairs":{}};hs={"pairs":{}};cache=m15_strategy._bootstrap_cache(rows)
        signals={}; start_ts=int(start.timestamp());end_ts=int(end.timestamp())
        for n in range(2100,len(rows)+1):
          bt=int(rows[n-1]["time"])
          mr=m15_strategy.evaluate(a.pair,rows[:n],spread,_state=ms,_save=False,_cache=cache,_end=n)
          if a.m15 and mr and mr.get("strategyAllowed") and str(mr.get("pattern","")) in ("P1","P2","P3") and start_ts<=bt<=end_ts:
            sid=f"REPLAY-M15-{a.pair}-{bt}-{mr.get('pattern','')}-{mr['direction']}"
            signals[sid]={"SignalID":sid,"SignalTime":datetime.fromtimestamp(bt,timezone.utc).isoformat(),"Pair":a.pair,"Direction":mr["direction"],"Rule":"M15","TF":"M15","Pullback":mr.get("pattern",""),"Decision":"SIGNAL_ONLY","Status":"監視中","Executed":"NO","SkipReason":"","EntryPrice":mr.get("entry",""),"InitialSL":mr.get("sl",""),"InitialRiskPips":(abs(float(mr.get("entry",0))-float(mr.get("sl",0)))/m15_strategy.pip_size(a.pair)),"Replay":"YES"}
          if a.h1 and ((bt%3600)//60)==45:
            hr=h1_strategy.evaluate(a.pair,rows[:n],spread,_state=hs,_save=False)
            if hr and hr.get("strategyAllowed") and str(hr.get("pattern",""))=="W1" and start_ts<=bt<=end_ts:
              sid=f"REPLAY-H1-{a.pair}-{bt}-{hr.get('pattern','')}-{hr['direction']}"
              signals[sid]={"SignalID":sid,"SignalTime":datetime.fromtimestamp(bt,timezone.utc).isoformat(),"Pair":a.pair,"Direction":hr["direction"],"Rule":"H1","TF":"H1","Pullback":hr.get("pattern",""),"Decision":"SIGNAL_ONLY","Status":"監視中","Executed":"NO","SkipReason":"","EntryPrice":hr.get("entry",""),"InitialSL":hr.get("sl",""),"InitialRiskPips":(abs(float(hr.get("entry",0))-float(hr.get("sl",0)))/m15_strategy.pip_size(a.pair)),"Replay":"YES"}
        # M15 strategy already maintained its causal virtual ledger during replay.
        for t in (ms.get("pairs",{}).get(a.pair,{}) or {}).get("virtual_trades",{}).values():
          et=int(t.get("entry_time",0)); key=next((k for k,v in signals.items() if v["TF"]=="M15" and int(datetime.fromisoformat(v["SignalTime"]).timestamp())==et and v["Direction"]==t.get("direction")),None)
          if key and not t.get("open",False):
            v=signals[key];v.update({"Status":"決済","ExitTime":datetime.fromtimestamp(int(t.get("exit_time",0)),timezone.utc).isoformat(),"ExitPrice":t.get("exit",""),"Pips":((float(t["exit"])-float(t["entry"]))*(1 if t["direction"]=="BUY" else -1)/m15_strategy.pip_size(a.pair)),"R":t.get("final_r","")})
        # H1 entries share the M15 causal exit model. Inject each H1 trade only
        # when its entry bar has actually been reached; never expose future entries.
        if a.h1:
          hps={"virtual_trades":{}}
          pending=sorted([v for v in signals.values() if v["TF"]=="H1"],key=lambda v:int(datetime.fromisoformat(v["SignalTime"]).timestamp()))
          pi=0
          for i,row in enumerate(cache["rows"]):
            bt=int(row["time"])
            while pi<len(pending) and int(datetime.fromisoformat(pending[pi]["SignalTime"]).timestamp())<=bt:
              v=pending[pi];et=int(datetime.fromisoformat(v["SignalTime"]).timestamp());risk=abs(float(v["EntryPrice"])-float(v["InitialSL"]))
              if risk>0:
                tid="H1REPLAY:"+v["SignalID"]
                hps["virtual_trades"][tid]={"trade_id":tid,"entered":True,"open":True,"entry":float(v["EntryPrice"]),"sl":float(v["InitialSL"]),"risk":risk,"direction":v["Direction"],"entry_time":et,"trailing":False,"spread_r":spread/risk,"strategy":"H1"}
              pi+=1
            if not hps["virtual_trades"]:continue
            pv=[p for p in cache["pv"] if p["confirmed"]<=i]
            m15_strategy.update_virtual_ledger(hps,row,pv,i)
          for t in hps.get("virtual_trades",{}).values():
            if not str(t.get("trade_id","")).startswith("H1REPLAY:") or t.get("open",False):continue
            sid=str(t["trade_id"]).split("H1REPLAY:",1)[1]
            if sid in signals:
              v=signals[sid];v.update({"Status":"決済","ExitTime":datetime.fromtimestamp(int(t.get("exit_time",0)),timezone.utc).isoformat(),"ExitPrice":t.get("exit",""),"Pips":((float(t["exit"])-float(t["entry"]))*(1 if t["direction"]=="BUY" else -1)/m15_strategy.pip_size(a.pair)),"R":t.get("final_r","")})
        sess=requests.Session()
        for v in signals.values():
          res=sess.post(a.gas_url,json={"action":"saveEASignal","data":v},timeout=20);res.raise_for_status()
          body=res.json()
          if body.get("success") is False:raise RuntimeError(body.get("error","GAS save failed"))
        m15_count=sum(1 for v in signals.values() if v.get("TF")=="M15");h1_count=sum(1 for v in signals.values() if v.get("TF")=="H1")
        print(json.dumps({"success":True,"pair":a.pair,"count":len(signals),"m15_count":m15_count,"h1_count":h1_count},ensure_ascii=False))
    finally:mt5.shutdown()
if __name__=="__main__":main()
