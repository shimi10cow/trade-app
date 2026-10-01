"""Capture historical deals from the account currently selected in the normal MT5 terminal.

Run this once per account after switching the logged-in account in MT5. No order is sent or
modified. Captures are merged/deduplicated locally, so rerunning the same account is safe.
"""
import argparse,csv,json,pathlib
from datetime import datetime,timezone,timedelta
import MetaTrader5 as mt5
ROOT=pathlib.Path(__file__).parent;OUT=ROOT/"analysis_input";JSON_PATH=OUT/"mt5_deals.json";CSV_PATH=OUT/"mt5_deals.csv"
def iso(ts):return datetime.fromtimestamp(float(ts),timezone.utc).isoformat() if ts else ""
def base_symbol(s):
 s=str(s or "").upper().replace("#","");return "XAUUSD" if s=="GOLD" else s
def load_old():
 try:return json.loads(JSON_PATH.read_text(encoding="utf-8"))
 except Exception:return []
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--years",type=float,default=10);args=ap.parse_args()
 if not mt5.initialize():raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}\nKeep MT5 open and try again.")
 try:
  a=mt5.account_info()
  if not a:raise SystemExit("MT5 account_info unavailable")
  login=str(a.login);server=str(getattr(a,"server","") or "");end=datetime.now(timezone.utc);start=end-timedelta(days=int(args.years*365.25))
  deals=mt5.history_deals_get(start,end)
  if deals is None:raise SystemExit(f"history_deals_get failed: {mt5.last_error()}")
  fresh=[]
  for d in deals:
   if int(getattr(d,"position_id",0) or 0)<=0:continue
   fresh.append({"account":login,"server":server,"ticket":str(d.ticket),"order":str(getattr(d,"order",0) or 0),"position_id":str(d.position_id),"time":iso(getattr(d,"time",0)),"time_msc":int(getattr(d,"time_msc",0) or 0),"symbol":base_symbol(d.symbol),"broker_symbol":str(d.symbol),"type":int(d.type),"entry":int(d.entry),"magic":int(getattr(d,"magic",0) or 0),"volume":float(getattr(d,"volume",0) or 0),"price":float(getattr(d,"price",0) or 0),"profit":float(getattr(d,"profit",0) or 0),"commission":float(getattr(d,"commission",0) or 0),"swap":float(getattr(d,"swap",0) or 0),"fee":float(getattr(d,"fee",0) or 0),"comment":str(getattr(d,"comment","") or "")})
  old=load_old();merged={(str(x.get("server","")),str(x.get("account","")),str(x.get("ticket",""))):x for x in old};before=len(merged)
  for x in fresh:merged[(x["server"],x["account"],x["ticket"])]=x
  rows=sorted(merged.values(),key=lambda x:(x["time_msc"],x["account"],x["ticket"]));OUT.mkdir(exist_ok=True)
  JSON_PATH.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
  if rows:
   with open(CSV_PATH,"w",newline="",encoding="utf-8-sig") as fh:
    w=csv.DictWriter(fh,fieldnames=list(rows[0].keys()));w.writeheader();w.writerows(rows)
  accounts=sorted({(x["server"],x["account"]) for x in rows})
  print("\n=== MT5 HISTORY CAPTURED ===");print(f"Current account : {login}");print(f"Server          : {server}");print(f"Deals this run  : {len(fresh)}");print(f"New/updated     : {len(rows)-before}");print(f"Total deals     : {len(rows)}");print(f"Accounts saved  : {len(accounts)}");print(f"Saved           : {JSON_PATH}");print("\nSaved accounts:")
  for srv,acc in accounts:print(f"  - {acc} / {srv}")
  print("\nNEXT: switch MT5 to the next account and run this same command again.")
 finally:mt5.shutdown()
if __name__=="__main__":main()
