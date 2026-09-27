"""MT5 position sync for the EA terminal plus optional additional MT5 terminals/accounts.

The EA's primary terminal stays connected in main.py. Extra accounts are read by short-lived
worker processes so MetaTrader5's process-global connection cannot switch the live EA account.
No closed history is backfilled: current open positions are the baseline, then only their exits
and future positions are synchronized.
"""
import json, os, time, subprocess, sys, pathlib
from datetime import datetime, timezone
import MetaTrader5 as mt5

ROOT=pathlib.Path(__file__).parent
STATE_PATH=ROOT/"mt5_position_sync.json"
ACCOUNTS_FILE=pathlib.Path(os.getenv("EA_MT5_ACCOUNTS_FILE",str(ROOT/"mt5_accounts.json")))
EXTRA_POLL_SEC=max(2,int(os.getenv("EA_MT5_ACCOUNTS_POLL_SEC","10")))
_last_extra_poll=0.0

def _load(path=STATE_PATH):
    try:return json.loads(path.read_text(encoding="utf-8"))
    except Exception:return {"startedAt":0,"positions":{}}

def _save(s,path=STATE_PATH):
    tmp=path.with_suffix(path.suffix+".tmp")
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(s,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)

def _iso(ts):return datetime.fromtimestamp(float(ts),timezone.utc).isoformat() if ts else ""
def _base(symbol):
    s=str(symbol or "").upper().replace("#","")
    return "XAUUSD" if s=="GOLD" else s
def _direction(pos):return "BUY" if int(pos.type)==mt5.POSITION_TYPE_BUY else "SELL"
def _source(pos,magic):return "EA" if int(getattr(pos,"magic",0) or 0)==int(magic) else "MT5-MANUAL"

def _payload(pos,magic,account,server=""):
    source=_source(pos,magic);ticket=str(pos.ticket)
    return {"SyncKey":f"{server}:{account}:{ticket}","Account":str(account),"Server":str(server),"Ticket":ticket,
      "Source":source,"TradeType":"EA" if source=="EA" else "裁量","Pair":_base(pos.symbol),
      "Direction":_direction(pos),"EntryTime":_iso(getattr(pos,"time",0)),"EntryPrice":float(pos.price_open),
      "Lot":float(pos.volume),"SL":float(getattr(pos,"sl",0) or 0),"TP":float(getattr(pos,"tp",0) or 0),"Status":"OPEN"}

def _closed_payload(old):
    deals=mt5.history_deals_get(position=int(old["Ticket"])) or []
    exits=[d for d in deals if int(getattr(d,"entry",-1)) in (mt5.DEAL_ENTRY_OUT,mt5.DEAL_ENTRY_OUT_BY)]
    if not exits:return None
    vol=sum(float(getattr(d,"volume",0) or 0) for d in exits)
    px=sum(float(d.price)*float(getattr(d,"volume",0) or 0) for d in exits)/vol if vol else float(exits[-1].price)
    last=max(exits,key=lambda d:getattr(d,"time_msc",getattr(d,"time",0)))
    profit=sum(float(getattr(d,"profit",0) or 0)+float(getattr(d,"commission",0) or 0)+float(getattr(d,"swap",0) or 0)+float(getattr(d,"fee",0) or 0) for d in exits)
    out=dict(old);out.update({"Status":"CLOSED","ExitTime":_iso(getattr(last,"time",0)),"ExitPrice":px,"Profit":profit});return out

def _scan_connected(magic,state_path=STATE_PATH):
    a=mt5.account_info()
    if not a:return []
    account=str(a.login);server=str(getattr(a,"server","") or "")
    state=_load(state_path);known=state.setdefault("positions",{})
    current={str(p.ticket):p for p in (mt5.positions_get() or [])};events=[]
    for ticket,pos in current.items():
        payload=_payload(pos,magic,account,server);prev=known.get(ticket)
        changed=prev is None or prev.get("Status")!="OPEN" or any(float(prev.get(k,0) or 0)!=float(payload[k]) for k in ("Lot","SL","TP"))
        known[ticket]=payload
        if changed:events.append(payload)
    for ticket,old in list(known.items()):
        if old.get("Status")!="OPEN" or ticket in current:continue
        closed=_closed_payload(old)
        if closed:known[ticket]=closed;events.append(closed)
    if not state.get("startedAt"):state["startedAt"]=time.time()
    _save(state,state_path);return events

def _account_configs():
    try:
        raw=json.loads(ACCOUNTS_FILE.read_text(encoding="utf-8"))
        rows=raw.get("accounts",raw) if isinstance(raw,dict) else raw
        return [x for x in rows if isinstance(x,dict) and x.get("enabled",True)]
    except FileNotFoundError:return []
    except Exception as e:raise RuntimeError(f"invalid MT5 accounts file {ACCOUNTS_FILE}: {e}")

def _worker(config,magic):
    payload=json.dumps({"config":config,"magic":magic},ensure_ascii=False)
    r=subprocess.run([sys.executable,str(ROOT/"mt5_account_worker.py"),payload],capture_output=True,text=True,timeout=20)
    if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout or "MT5 account worker failed").strip())
    x=json.loads(r.stdout or "{}")
    if not x.get("ok"):raise RuntimeError(x.get("error","MT5 account worker failed"))
    return x.get("events") or []

def sync(magic,enqueue):
    global _last_extra_poll
    # Primary live EA account: never disconnect or switch it.
    for event in _scan_connected(magic):enqueue("syncMT5Trade",{"data":event})
    now=time.time()
    if now-_last_extra_poll<EXTRA_POLL_SEC:return
    _last_extra_poll=now
    primary=mt5.account_info();primary_key=(str(primary.login),str(getattr(primary,"server","") or "")) if primary else ("","")
    for cfg in _account_configs():
        key=(str(cfg.get("login","")),str(cfg.get("server","")))
        if key==primary_key:continue
        safe={k:cfg.get(k) for k in ("name","terminalPath","login","server","passwordEnv","enabled")}
        for event in _worker(safe,magic):enqueue("syncMT5Trade",{"data":event})
