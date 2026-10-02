"""Read-only MT5 manual trade importer.

Polls the app request queue, reads ONLY the account currently logged in to the
single MT5 terminal, and uploads deals/positions to Google Sheets via GAS.
It never sends orders and never modifies SL/TP.
"""
import os,time,logging
from datetime import datetime,timezone,timedelta
import requests
import MetaTrader5 as mt5

DEFAULT_GAS_URL="https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
GAS_URL=os.getenv("EA_GAS_URL",DEFAULT_GAS_URL)
POLL_SEC=max(1,int(os.getenv("MT5_IMPORT_POLL_SEC","1")))
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")

def gas_get(action,**params):
    r=requests.get(GAS_URL,params={"action":action,**params},timeout=10);r.raise_for_status()
    x=r.json();return x.get("data",x)

def gas_post(action,**payload):
    r=requests.post(GAS_URL,json={"action":action,**payload},timeout=20);r.raise_for_status()
    x=r.json()
    if x.get("success") is False:raise RuntimeError(str(x))
    return x

def iso(ts):
    return datetime.fromtimestamp(float(ts),timezone.utc).isoformat() if ts else ""

def base_symbol(symbol):
    s=str(symbol or "").upper().replace("#","")
    return "XAUUSD" if s=="GOLD" else s

def side_from_deal(d):
    t=int(getattr(d,"type",-1))
    if t==mt5.DEAL_TYPE_BUY:return "BUY"
    if t==mt5.DEAL_TYPE_SELL:return "SELL"
    return ""

def fetch_current_account(request):
    if not mt5.initialize():raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        a=mt5.account_info()
        if not a:raise RuntimeError("MT5 account_info unavailable")
        account=str(a.login);server=str(getattr(a,"server","") or "")
        gas_post("updateMT5ImportRequest",data={"RequestID":request.get("RequestID",""),"Status":"DONE","Account":account,"Server":server,"Message":"ACCOUNT_INFO"})
        logging.info("MT5 account info account=%s server=%s",account,server)
        return {"account":account,"server":server}
    finally:
        mt5.shutdown()

def import_current_account(request):
    if not mt5.initialize():raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        a=mt5.account_info()
        if not a:raise RuntimeError("MT5 account_info unavailable")
        account=str(a.login);server=str(getattr(a,"server","") or "")
        days=max(1,min(3650,int(request.get("Days") or 30)))
        end=datetime.now(timezone.utc)+timedelta(minutes=5)
        since=request.get("Since")
        if since:
            try:
                start=datetime.fromisoformat(str(since).replace("Z","+00:00"))-timedelta(minutes=5)
                if start.tzinfo is None:start=start.replace(tzinfo=timezone.utc)
            except (ValueError,TypeError):
                start=end-timedelta(days=days)
        else:
            start=end-timedelta(days=days)
        deals=list(mt5.history_deals_get(start,end) or [])
        positions=list(mt5.positions_get() or [])
        rows=[]
        for d in deals:
            side=side_from_deal(d)
            if not side:continue
            deal=str(getattr(d,"ticket","") or "")
            posid=str(getattr(d,"position_id","") or "")
            rows.append({
              "ExecutionID":f"{server}:{account}:DEAL:{deal}","Account":account,"Server":server,
              "Ticket":str(getattr(d,"order","") or ""),"Deal":deal,"PositionID":posid,
              "Source":"MT5-MANUAL","Pair":base_symbol(getattr(d,"symbol","")),"Direction":side,
              "DealEntry":str(getattr(d,"entry","")),"DealTime":iso(getattr(d,"time",0)),
              "DealPrice":float(getattr(d,"price",0) or 0),"DealVolume":float(getattr(d,"volume",0) or 0),
              "Profit":float(getattr(d,"profit",0) or 0),"Swap":float(getattr(d,"swap",0) or 0),
              "Status":"RAW","ImportStatus":"未確認"
            })
        for p in positions:
            side="BUY" if int(p.type)==mt5.POSITION_TYPE_BUY else "SELL"
            ticket=str(p.ticket);posid=str(getattr(p,"identifier",ticket) or ticket)
            rows.append({
              "ExecutionID":f"{server}:{account}:POSITION:{ticket}","Account":account,"Server":server,
              "Ticket":ticket,"PositionID":posid,"Source":"MT5-MANUAL","Pair":base_symbol(p.symbol),
              "Direction":side,"EntryTime":iso(getattr(p,"time",0)),"EntryPrice":float(p.price_open),
              "Lot":float(p.volume),"SL":float(getattr(p,"sl",0) or 0),"TP":float(getattr(p,"tp",0) or 0),
              "Status":"OPEN","ImportStatus":"未確認"
            })
        result=gas_post("saveMT5ImportBatch",requestId=request.get("RequestID",""),account=account,server=server,data=rows)
        logging.info("MT5 import account=%s server=%s rows=%s",account,server,len(rows))
        return result
    finally:
        mt5.shutdown()

def run():
    logging.info("MT5 import worker started (READ ONLY)")
    while True:
        try:
            req=gas_get("getMT5ImportRequest") or {}
            if isinstance(req,dict) and str(req.get("Status","")).upper()=="PENDING":
                rid=str(req.get("RequestID",""))
                gas_post("updateMT5ImportRequest",data={"RequestID":rid,"Status":"RUNNING","Message":""})
                try:
                    fetch_current_account(req) if str(req.get("Mode","")).upper()=="ACCOUNT" else import_current_account(req)
                except Exception as e:
                    gas_post("updateMT5ImportRequest",data={"RequestID":rid,"Status":"ERROR","Message":str(e)[:1000]})
                    raise
        except Exception as e:
            logging.warning("MT5 import poll failed: %s",e)
        time.sleep(POLL_SEC)

if __name__=="__main__":run()
