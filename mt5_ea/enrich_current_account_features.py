"""Fast read-only enrichment of MT5 master trades with M15/H1/H4 context."""
import csv,pathlib,bisect
from datetime import datetime,timezone,timedelta
import MetaTrader5 as mt5
ROOT=pathlib.Path(__file__).parent;PATH=ROOT/"analysis_output"/"master_trades.csv"
TFS={"m15":mt5.TIMEFRAME_M15,"h1":mt5.TIMEFRAME_H1,"h4":mt5.TIMEFRAME_H4}
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
 ks=[sum(raw[i-slow+1:i+1])/slow for i in range(slow-1,len(raw))];ds=[sum(ks[i-dp+1:i+1])/dp for i in range(dp-1,len(ks))]
 return (ks[-1] if ks else None,ds[-1] if ds else None)
def calc(r,p):
 c=[x["close"] for x in r];o={}
 if len(c)<30:return {p+"_feature_error":"insufficient rates"}
 last=c[-1];o[p+"_close"]=last
 for n in (20,75,200,480):
  m=sma(c,n);o[f"{p}_ma{n}"]=m;o[f"{p}_ma{n}_dist_pct"]=(last/m-1)*100 if m else None
 k,d=stoch(r);o[p+"_stoch_k"]=k;o[p+"_stoch_d"]=d;o[p+"_atr14"]=atr(r)
 o[p+"_ma20_gt_75"]=(o[p+"_ma20"]>o[p+"_ma75"]) if o[p+"_ma20"] and o[p+"_ma75"] else None;o[p+"_ma200_gt_480"]=(o[p+"_ma200"]>o[p+"_ma480"]) if o[p+"_ma200"] and o[p+"_ma480"] else None
 o[p+"_ma200_slope12_pct"]=slope(c,200,12);o[p+"_ma480_slope24_pct"]=slope(c,480,24);return o
def main():
 if not PATH.exists():raise SystemExit("Run py analyze_captured_history.py first.")
 print("Connecting to current MT5 account...",flush=True)
 if not mt5.initialize():raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
 try:
  a=mt5.account_info()
  if not a:raise SystemExit("No MT5 account")
  login=str(a.login);server=str(a.server)
  with open(PATH,encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
  targets=[x for x in rows if x.get("account")==login and x.get("server")==server]
  if not targets:raise SystemExit(f"No master trades for current account {login} / {server}")
  print(f"Account: {login} / {server} | trades: {len(targets)}",flush=True);bysym={}
  for x in targets:bysym.setdefault(x.get("broker_symbol") or x["symbol"],[]).append(x)
  caches={}
  for sym,xs in bysym.items():
   times=[datetime.fromisoformat(x["entry_time"].replace("Z","+00:00")).astimezone(timezone.utc) for x in xs];lo=min(times)-timedelta(days=100);hi=max(times)+timedelta(hours=1)
   print(f"Loading {sym}: {lo.date()} -> {hi.date()} ...",flush=True)
   for p,tf in TFS.items():
    arr=mt5.copy_rates_range(sym,tf,lo,hi);rr=[] if arr is None else [{"time":int(z["time"]),"high":float(z["high"]),"low":float(z["low"]),"close":float(z["close"])} for z in arr];caches[(sym,p)]=(rr,[z["time"] for z in rr]);print(f"  {p.upper()}: {len(rr)} bars",flush=True)
  for i,x in enumerate(targets,1):
   t=datetime.fromisoformat(x["entry_time"].replace("Z","+00:00")).astimezone(timezone.utc);ts=int(t.timestamp());sym=x.get("broker_symbol") or x["symbol"]
   for p in TFS:
    rr,tt=caches[(sym,p)];j=bisect.bisect_left(tt,ts);window=rr[max(0,j-1300):j]
    for k,v in calc(window,p).items():x[k]="" if v is None else v
   x["objective_features_status"]="OK"
   if i==1 or i%100==0 or i==len(targets):print(f"Processed {i}/{len(targets)}",flush=True)
  fields=list(rows[0].keys());extras=[]
  for x in rows:
   for k in x:
    if k not in fields and k not in extras:extras.append(k)
  with open(PATH,"w",encoding="utf-8-sig",newline="") as f:
   w=csv.DictWriter(f,fieldnames=fields+extras);w.writeheader();w.writerows(rows)
  print("\n=== OBJECTIVE FEATURES CAPTURED ===");print(f"Account : {login} / {server}");print(f"Trades  : {len(targets)}");print(f"Saved   : {PATH}");print("\nSwitch MT5 to the next account and run this command again.")
 finally:mt5.shutdown()
if __name__=="__main__":main()
