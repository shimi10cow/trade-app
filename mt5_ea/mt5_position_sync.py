"""Synchronize current/future MT5 positions to Trade Tracker. No historical backfill."""
import json, os, time
from datetime import datetime, timezone
import MetaTrader5 as mt5

STATE_PATH=os.path.join(os.path.dirname(__file__),"mt5_position_sync.json")

def _load():
    try:
        with open(STATE_PATH,"r",encoding="utf-8") as f:return json.load(f)
    except Exception:return {"startedAt":0,"positions":{}}

def _save(s):
    tmp=STATE_PATH+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        json.dump(s,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())
    os.replace(tmp,STATE_PATH)

def _iso(ts):
    return datetime.fromtimestamp(float(ts),timezone.utc).isoformat() if ts else ""

def _base(symbol):
    s=str(symbol or "").upper().replace("#","")
    return "XAUUSD" if s=="GOLD" else s

def _direction(pos):
    return "BUY" if int(pos.type)==mt5.POSITION_TYPE_BUY else "SELL"

def _source(pos,magic):
    return "EA" if int(getattr(pos,"magic",0) or 0)==int(magic) else "MT5-MANUAL"

def _payload(pos,magic,account):
    source=_source(pos,magic)
    ticket=str(pos.ticket)
    return {
      "SyncKey":f"{account}:{ticket}","Account":str(account),"Ticket":ticket,
      "Source":source,"TradeType":"EA" if source=="EA" else "裁量",
      "Pair":_base(pos.symbol),"Direction":_direction(pos),
      "EntryTime":_iso(getattr(pos,"time",0)),"EntryPrice":float(pos.price_open),
      "Lot":float(pos.volume),"SL":float(getattr(pos,"sl",0) or 0),
      "TP":float(getattr(pos,"tp",0) or 0),"Status":"OPEN"
    }

def _closed_payload(old,account):
    ticket=int(old["Ticket"])
    deals=mt5.history_deals_get(position=ticket) or []
    exits=[d for d in deals if int(getattr(d,"entry",-1)) in (mt5.DEAL_ENTRY_OUT,mt5.DEAL_ENTRY_OUT_BY)]
    if not exits:return None
    vol=sum(float(getattr(d,"volume",0) or 0) for d in exits)
    px=(sum(float(d.price)*float(getattr(d,"volume",0) or 0) for d in exits)/vol) if vol else float(exits[-1].price)
    last=max(exits,key=lambda d:getattr(d,"time_msc",getattr(d,"time",0)))
    profit=sum(float(getattr(d,"profit",0) or 0)+float(getattr(d,"commission",0) or 0)+float(getattr(d,"swap",0) or 0)+float(getattr(d,"fee",0) or 0) for d in exits)
    out=dict(old)
    out.update({"Status":"CLOSED","ExitTime":_iso(getattr(last,"time",0)),"ExitPrice":px,"Profit":profit})
    return out

def sync(magic,enqueue):
    """Sync current positions immediately; only closures of positions seen by this process are imported."""
    a=mt5.account_info()
    if not a:return
    account=str(a.login)
    state=_load()
    current={str(p.ticket):p for p in (mt5.positions_get() or [])}
    known=state.setdefault("positions",{})
    # Current open positions are intentionally imported on first run.
    for ticket,pos in current.items():
        payload=_payload(pos,magic,account)
        prev=known.get(ticket)
        changed=(prev is None or prev.get("Status")!="OPEN" or
                 float(prev.get("Lot",0) or 0)!=payload["Lot"] or
                 float(prev.get("SL",0) or 0)!=payload["SL"] or
                 float(prev.get("TP",0) or 0)!=payload["TP"])
        known[ticket]=payload
        if changed:enqueue("syncMT5Trade",{"data":payload})
    # Only tickets observed open by this sync state can become closed: no old-history import.
    for ticket,old in list(known.items()):
        if old.get("Status")!="OPEN" or ticket in current:continue
        closed=_closed_payload(old,account)
        if closed:
            known[ticket]=closed
            enqueue("syncMT5Trade",{"data":closed})
    if not state.get("startedAt"):state["startedAt"]=time.time()
    _save(state)
