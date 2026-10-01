"""Enrich MT5-authoritative master trades with objective M15/H1/H4 context.

Run once per currently selected MT5 account. Existing rows for other accounts are preserved.
Read-only: never sends or modifies orders.
"""
import csv,math,pathlib
from datetime import datetime,timezone
import MetaTrader5 as mt5
ROOT=pathlib.Path(__file__).parent; PATH=ROOT/"analysis_output"/"master_trades.csv"
TFS={"m15":mt5.TIMEFRAME_M15,"h1":mt5.TIMEFRAME_H1,"h4":mt5.TIMEFRAME_H4}
def num(v):
 try:return float(v)
 except:return None
def sma(v,n):return sum(v[-n:])/n if len(v)>=n else None
def slope(v,n,lb):
 if len(v)<n+lb:return None
 a=sum(v[-n:])/n;b=sum(v[-n-lb:-lb])/n
 return (a/b-1)*100 if b else None
def atr(r,n=14):
 if len(r)<n+1:return None
 z=[max(r[i]["high"]-r[i]["low"],abs(r[i]["high"]-r[i-1]["close"]),abs(r[i]["low"]-r[i-1]["close"])) for i in range(1,len(r))]
 return sum(z[-n:])/n
def stoch(r,kp=14,slow=5,dp=3):
 raw=[]
 for i in range(kp-1,len(r)):
  w=r[i-kp+1:i+1];hi=max(x["high"] for x in w);lo=min(x["low"] for x in w)
  raw.append(50 if hi==lo else 100*(r[i]["close"]-lo)/(hi-lo))
 ks=[sum(raw[i-slow+1:i+1])/slow for i in range(slow-1,len(raw))]
 ds=[sum(ks[i-dp+1:i+1])/dp for i in range(dp-1,len(ks))]
 return (ks[-1] if ks else None,ds[-1] if ds else None)
def rates(sym,tf,t,count=1300):
 a=mt5.copy_rates_from(sym,tf,t,count)
 if a is None:return []
 return [{"time":int(x["time"]),"high":float(x["high"]),"low":float(x["low"]),"close":float(x["close"])} for x in a if int(x["time"])<int(t.timestamp())]
def feats(sym,t,prefix,tf):
 r=rates(sym,tf,t);c=[x["close"] for x in r];o={}
 if len(c)<30:return {prefix+"_feature_error":"rates unavailable"}
 last=c[-1];o[prefix+"_close"]=last
 for n in (20,75,200,480):
  m=sma(c,n);o[f"{prefix}_ma{n}"]=m;o[f"{prefix}_ma{n}_dist_pct"]=(last/m-1)*100 if m else None
 k,d=stoch(r);o[prefix+"_stoch_k"]=k;o[prefix+"_stoch_d"]=d;o[prefix+"_atr14"]=atr(r)
 o[prefix+"_ma20_gt_75"]=(o[prefix+"_ma20"]>o[prefix+"_ma75"]) if o[prefix+"_ma20"] and o[prefix+"_ma75"] else None
 o[prefix+"_ma200_gt_480"]=(o[prefix+"_ma200"]>o[prefix+"_ma480"]) if o[prefix+"_ma200"] and o[prefix+"_ma480"] else None
 o[prefix+"_ma200_slope12_pct"]=slope(c,200,12);o[prefix+"_ma480_slope24_pct"]=slope(c,480,24)
 return o
def main():
 if not PATH.exists():raise SystemExit("Run py analyze_captured_history.py first.")
 if not mt5.initialize():raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
 try:
  a=mt5.account_info()
  if not a:raise SystemExit("No MT5 account")
  login=str(a.login);server=str(a.server)
  with open(PATH,encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
  targets=[x for x in rows if x.get("account")==login and x.get("server")==server]
  if not targets:raise SystemExit(f"No master trades for current account {login} / {server}")
  ok=0
  for i,x in enumerate(targets,1):
   t=datetime.fromisoformat(x["entry_time"].replace("Z","+00:00")).astimezone(timezone.utc);sym=x.get("broker_symbol") or x["symbol"]
   for p,tf in TFS.items():
    for k,v in feats(sym,t,p,tf).items():x[k]="" if v is None else v
   x["objective_features_status"]="OK";ok+=1
   if i%50==0:print(f"{i}/{len(targets)}")
  fields=list(rows[0].keys())
  extras=[]
  for x in rows:
   for k in x:
    if k not in fields and k not in extras:extras.append(k)
  with open(PATH,"w",encoding="utf-8-sig",newline="") as f:
   w=csv.DictWriter(f,fieldnames=fields+extras);w.writeheader();w.writerows(rows)
  print("\n=== OBJECTIVE FEATURES CAPTURED ===");print(f"Account : {login} / {server}");print(f"Trades  : {ok}");print(f"Saved   : {PATH}");print("\nSwitch MT5 to the next account and run this command again.")
 finally:mt5.shutdown()
if __name__=="__main__":main()
