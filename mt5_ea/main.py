"""Hybrid EA runner. Start with DRY_RUN=true. Windows + MT5 terminal + Python 3.11."""
import os,time,json,logging,threading,queue,sqlite3
from datetime import datetime,timezone
import requests
import MetaTrader5 as mt5
from m15_strategy import evaluate as evaluate_m15_strategy, load_state as load_m15_state

DEFAULT_GAS_URL="https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
GAS_URL=os.getenv("EA_GAS_URL",DEFAULT_GAS_URL)
DRY_RUN=os.getenv("EA_DRY_RUN","true").lower()=="true"
POLL_SEC=int(os.getenv("EA_POLL_SEC","2"))
MAGIC=int(os.getenv("EA_MAGIC","560001"))
PAIR_OVERRIDE=[x.strip() for x in os.getenv("EA_PAIRS","").split(",") if x.strip()]
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
last_bar={}
_cache={"settings":None,"settings_at":0.0,"env":None,"env_at":0.0}
_cache_lock=threading.Lock()
_stop=threading.Event()
_outbox=queue.Queue()
SETTINGS_MAX_STALE=900
ENV_MAX_STALE=7200\nOUTBOX_DB=os.getenv("EA_OUTBOX_DB",os.path.join(os.path.dirname(__file__),"ea_outbox.sqlite3"))

def gas_get(action,**params):
    if not GAS_URL:return {}
    r=requests.get(GAS_URL,params={"action":action,**params},timeout=8);r.raise_for_status()
    x=r.json();return x.get("data",x)

def gas_post(action,data):
    if not GAS_URL: raise RuntimeError("EA_GAS_URL is not configured")
    r=requests.post(GAS_URL,json={"action":action,**data},timeout=10);r.raise_for_status()
    x=r.json()
    if x.get("success") is False: raise RuntimeError("GAS rejected request: "+str(x))
    return x.get("data",x)

def connect():
    if not mt5.initialize():raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    a=mt5.account_info()
    if not a:raise RuntimeError("MT5 account_info unavailable")
    logging.info("MT5 connected login=%s server=%s balance=%s DRY_RUN=%s",a.login,a.server,a.balance,DRY_RUN)

def bars(symbol,tf,count=3000):
    rates=mt5.copy_rates_from_pos(symbol,tf,0,count)
    if rates is None or len(rates)<3:raise RuntimeError(f"{symbol}: insufficient rates")
    # Drop bar 0: it is still forming. All decisions use closed candles only.
    return rates[:-1]

def pair_name(x):
    return str(x.get("PairName（元）") or x.get("PairName") or x.get("Pair") or x.get("通貨ペア") or x.get("pair") or "").strip() if isinstance(x,dict) else ""

def resolve_symbol(base):
    if mt5.symbol_info(base): return base
    b="".join(c for c in base.upper() if c.isalnum())
    aliases=[b]+(["GOLD"] if b=="XAUUSD" else [])
    hits=[x.name for x in (mt5.symbols_get() or []) if any(a in "".join(c for c in x.name.upper() if c.isalnum()) for a in aliases)]
    hits.sort(key=lambda n:(0 if "".join(c for c in n.upper() if c.isalnum()).startswith(b) else 1,len(n)))
    return hits[0] if hits else None

def truth(v,default=False):
    if v is None or v=="": return default
    return str(v).strip().lower() in ("1","true","on","yes","有効","on（有効）")

def pair_settings():
    """Normalize the existing Trade Tracker EA_Settings/App_Settings contract."""
    try:
        rows=gas_get("getEASettings") or []
        app=gas_get("getAppSettings") or {}
        cfg={"globalEntry":truth(app.get("globalEntry"),False),"totalRiskCapEnabled":truth(app.get("totalRiskCapEnabled") or app.get("総同時Risk上限ON"),False),"totalRiskCap":float(app.get("totalRiskCap") or app.get("総同時Risk上限%") or 0),"pairs":{}}
        for r in rows if isinstance(rows,list) else []:
            p=pair_name(r)
            if not p: continue
            mode=str(r.get("稼働方法") or "stop").strip().lower()
            if mode in ("自動","auto"): mode="auto"
            elif mode in ("signal","signal-only","シグナルのみ"): mode="signal"
            else: mode="stop"
            cfg["pairs"][p]={
                "mode":mode,
                "direction":r.get("許可方向") or "Both",
                "m15":truth(r.get("M15"),True),
                "h1":truth(r.get("H1"),False),
                "riskType":r.get("Lot方式") or "fixedLot",
                "riskValue":float(r.get("Lot値") or 0.01),
                "riskCapEnabled":truth(r.get("Risk上限ON"),True),
                "riskCap":float(r.get("Risk上限%") or 1),
                "autoExit":str(r.get("決済方法") or "auto").lower() not in ("off","manual","裁量")
            }
        return cfg
    except Exception as e:
        logging.error("settings fetch failed: %s",e)
        return None

def environment():
    try:return gas_get("getPairs") or []
    except Exception as e:
        logging.error("environment fetch failed: %s",e);return None

def evaluate_m15(base_symbol,broker_symbol,closed_bars):
    tick=mt5.symbol_info_tick(broker_symbol)
    spread=0.0
    if tick and tick.ask and tick.bid: spread=max(0.0,float(tick.ask)-float(tick.bid))
    return evaluate_m15_strategy(base_symbol,closed_bars,spread)

def allowed(sig,cfg,env):
    if not sig:return False,"NO_SIGNAL"
    if not sig.get("strategyAllowed",False):return False,sig.get("strategyReason","STRATEGY_REJECT")
    if not cfg.get("globalEntry",False):return False,"GLOBAL_STOP"
    pc=(cfg.get("pairs") or {}).get(sig["symbol"],{})
    mode=pc.get("mode","stop")
    if mode=="stop":return False,"PAIR_STOP"
    if mode=="signal":return False,"SIGNAL_ONLY"
    if mode!="auto":return False,"INVALID_MODE"
    if not pc.get("m15",True):return False,"M15_OFF"
    d=str(pc.get("direction","Both")).upper()
    if d not in ("BOTH","両方",sig["direction"].upper()):return False,"DIRECTION_BLOCK"
    return True,"OK"


def env_value(env,*keys):
    for k in keys:
        if k in env and env.get(k) not in (None,""):return env.get(k)
    return None

def environment_allowed(sig,env):
    if not isinstance(env,dict) or not env:return False,"ENV_MISSING"
    stamp=env_value(env,"環境確認日時","確認日時","更新日時","EnvironmentConfirmedAt","confirmedAt","updatedAt")
    if stamp:
        try:
            dt=datetime.fromisoformat(str(stamp).replace("Z","+00:00"))
            if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc)-dt.astimezone(timezone.utc)).total_seconds()>ENV_MAX_STALE:return False,"ENV_EXPIRED"
        except Exception:return False,"ENV_TIME_INVALID"
    push=str(env_value(env,"TL 推進","TL推進","TL_推進") or "").upper()
    counter=str(env_value(env,"TL 逆トレ","TL逆トレ","TL_逆トレ") or "").upper()
    if push or counter:
        side=sig["direction"].upper()
        if side not in (push,counter):return False,"ENV_DIRECTION_BLOCK"
    return True,"OK"

def open_ea_risk():
    total=0.0
    for p in mt5.positions_get() or []:
        if int(getattr(p,"magic",0))!=MAGIC or not getattr(p,"sl",0):continue
        side="BUY" if p.type==mt5.POSITION_TYPE_BUY else "SELL"
        try:total+=loss_for(p.symbol,side,float(p.volume),float(p.price_open),float(p.sl))
        except Exception:pass
    return total

def total_risk_allowed(symbol,direction,lot,entry,sl,cfg):
    if not cfg.get("totalRiskCapEnabled",False):return True
    a=mt5.account_info()
    if not a or float(a.balance)<=0:return False
    cap=float(a.balance)*float(cfg.get("totalRiskCap",0) or 0)/100.0
    return open_ea_risk()+loss_for(symbol,direction,lot,entry,sl)<=cap+1e-8

def modify_position_sl(position,new_sl):
    if DRY_RUN:return True
    req={"action":mt5.TRADE_ACTION_SLTP,"position":position.ticket,"symbol":position.symbol,"sl":float(new_sl),"tp":float(position.tp or 0),"magic":MAGIC}
    r=mt5.order_send(req)
    return bool(r and r.retcode==mt5.TRADE_RETCODE_DONE)
\ndef loss_for(symbol,direction,lot,entry,sl):
    typ=mt5.ORDER_TYPE_BUY if direction.upper()=="BUY" else mt5.ORDER_TYPE_SELL
    p=mt5.order_calc_profit(typ,symbol,lot,entry,sl)
    if p is None: raise RuntimeError(f"{symbol}: order_calc_profit failed")
    return abs(float(p))

def lot_for(symbol,direction,entry,sl,pc):
    info=mt5.symbol_info(symbol);acct=mt5.account_info()
    if not info or not acct:raise RuntimeError(f"{symbol}: broker/account specs unavailable")
    method=pc.get("riskType","fixedLot");value=float(pc.get("riskValue",0.01) or 0.01)
    if method=="fixedLot": lot=value
    else:
        target=value if method=="fixedLoss" else float(acct.balance)*value/100.0
        base=max(float(info.volume_min),float(info.volume_step or 0.01))
        base_loss=loss_for(symbol,direction,base,entry,sl)
        if base_loss<=0:raise RuntimeError(f"{symbol}: invalid SL risk")
        lot=base*target/base_loss
    step=float(info.volume_step or 0.01)
    lot=max(float(info.volume_min),min(float(info.volume_max),int(lot/step)*step))
    if pc.get("riskCapEnabled",True):
        cap=float(acct.balance)*float(pc.get("riskCap",1) or 1)/100.0
        if loss_for(symbol,direction,lot,entry,sl)>cap+1e-8:raise RuntimeError("RISK_CAP")
    return round(lot,8)

def account_snapshot():
    a=mt5.account_info()
    return {"Account":str(a.login) if a else "","Server":str(a.server) if a else "","AccountMode":"DEMO" if a and getattr(a,"trade_mode",None)==mt5.ACCOUNT_TRADE_MODE_DEMO else "REAL" if a else ""}

def send_order(sig,pc,cfg=None):
    symbol=sig["symbol"]
    if not mt5.symbol_select(symbol,True):raise RuntimeError(f"{symbol}: symbol_select failed")
    tick=mt5.symbol_info_tick(symbol)
    if not tick:raise RuntimeError(f"{symbol}: no tick")
    buy=sig["direction"].upper()=="BUY";price=tick.ask if buy else tick.bid
    if not price or price<=0:raise RuntimeError(f"{symbol}: market closed/no live price")
    if getattr(tick,"time",0) and time.time()-float(tick.time)>300:raise RuntimeError(f"{symbol}: stale tick")
    sl=float(sig["sl"])
    if (buy and sl>=price) or ((not buy) and sl<=price):raise RuntimeError(f"{symbol}: invalid SL side")
    lot=lot_for(symbol,sig["direction"],price,sl,pc)\n    if cfg is not None and not total_risk_allowed(symbol,sig["direction"],lot,price,sl,cfg):raise RuntimeError("TOTAL_RISK_CAP")
    req={"action":mt5.TRADE_ACTION_DEAL,"symbol":symbol,"volume":lot,
         "type":mt5.ORDER_TYPE_BUY if buy else mt5.ORDER_TYPE_SELL,
         "price":price,"sl":sl,"deviation":20,"magic":MAGIC,
         "comment":"HybridEA-M15","type_time":mt5.ORDER_TIME_GTC,"type_filling":mt5.symbol_info(symbol).filling_mode}
    if sig.get("tp"):req["tp"]=float(sig["tp"])
    check=mt5.order_check(req)
    if check is None:raise RuntimeError(f"order_check failed: {mt5.last_error()}")
    if DRY_RUN:return {"dry_run":True,"request":req,"order_check":str(check)}
    res=mt5.order_send(req)
    if res is None or res.retcode!=mt5.TRADE_RETCODE_DONE:raise RuntimeError(f"order_send failed: {res}")
    return {"dry_run":False,"order":res.order,"deal":res.deal,"price":res.price,"volume":res.volume}

def manage_ea_positions():
    """Keep EA-created MT5 SLs aligned with the strategy ledger even while new entries are stopped."""
    state=load_m15_state()
    for base,ps in (state.get("pairs") or {}).items():
        symbol=resolve_symbol(base)
        if not symbol:continue
        positions=[p for p in (mt5.positions_get(symbol=symbol) or []) if int(getattr(p,"magic",0))==MAGIC]
        positions.sort(key=lambda p:getattr(p,"time",0))
        trades=[t for t in (ps.get("trades") or {}).values() if t.get("entered") and t.get("open")]
        trades.sort(key=lambda t:t.get("entry_time",0))
        for p,t in zip(positions,trades):
            target=float(t.get("sl") or 0)
            current=float(getattr(p,"sl",0) or 0)
            buy=p.type==mt5.POSITION_TYPE_BUY
            improve=target>0 and (current<=0 or (buy and target>current) or ((not buy) and target<current))
            if improve and modify_position_sl(p,target):
                enqueue_gas("saveMT5Execution",{"data":{**account_snapshot(),"Source":"EA","Pair":base,"Direction":"BUY" if buy else "SELL","Ticket":p.ticket,"Event":"SL_UPDATE","SL":target,"EventTime":datetime.now(timezone.utc).isoformat()}})

def refresh_runtime_once():
    now=time.time(); settings=pair_settings(); env=environment()
    with _cache_lock:
        if settings is not None:_cache["settings"],_cache["settings_at"]=settings,now
        if env is not None:_cache["env"],_cache["env_at"]=env,now

def runtime_refresher():
    while not _stop.is_set():
        now=time.time()
        with _cache_lock:
            need_s=_cache["settings"] is None or now-_cache["settings_at"]>=300
            need_e=_cache["env"] is None or now-_cache["env_at"]>=3600
        if need_s:
            x=pair_settings()
            if x is not None:
                with _cache_lock:_cache["settings"],_cache["settings_at"]=x,time.time()
        if need_e:
            x=environment()
            if x is not None:
                with _cache_lock:_cache["env"],_cache["env_at"]=x,time.time()
        _stop.wait(2)

def cached_runtime():
    now=time.time()
    with _cache_lock:
        cfg=_cache["settings"]; env=_cache["env"]
        sa=now-_cache["settings_at"] if _cache["settings_at"] else 10**9
        ea=now-_cache["env_at"] if _cache["env_at"] else 10**9
    healthy=cfg is not None and env is not None and sa<=SETTINGS_MAX_STALE and ea<=ENV_MAX_STALE
    return cfg or {"globalEntry":False,"pairs":{}},env or [],healthy

def init_outbox():
    with sqlite3.connect(OUTBOX_DB) as db:
        db.execute("CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL)")
        db.commit()

def enqueue_gas(action,data):
    with sqlite3.connect(OUTBOX_DB) as db:
        db.execute("INSERT INTO outbox(action,payload,created) VALUES(?,?,?)",(action,json.dumps(data,ensure_ascii=False,default=str),time.time()))
        db.commit()

def outbox_worker():
    while not _stop.is_set():
        try:
            with sqlite3.connect(OUTBOX_DB) as db:
                row=db.execute("SELECT id,action,payload FROM outbox ORDER BY id LIMIT 1").fetchone()
            if not row:_stop.wait(1);continue
            oid,action,payload=row
            gas_post(action,json.loads(payload))
            with sqlite3.connect(OUTBOX_DB) as db:
                db.execute("DELETE FROM outbox WHERE id=?",(oid,));db.commit()
        except Exception as e:
            logging.error("GAS outbox failed: %s",e);_stop.wait(5)



def run():
    connect()
    init_outbox()
    refresh_runtime_once()
    threading.Thread(target=runtime_refresher,daemon=True).start()
    threading.Thread(target=outbox_worker,daemon=True).start()
    while not _stop.is_set():
        cfg,envs,runtime_ok=cached_runtime()
        envmap={pair_name(x):x for x in envs if isinstance(x,dict) and pair_name(x)}
        # Only explicit EA_Settings pairs are eligible. EA_PAIRS may narrow that set for testing,
        # but can never introduce an unconfigured pair.
        configured=set((cfg.get("pairs") or {}).keys())
        targets=(set(PAIR_OVERRIDE)&configured) if PAIR_OVERRIDE else configured
        manage_ea_positions()
        for base_symbol in sorted(targets):
            symbol=resolve_symbol(base_symbol)
            if not symbol:
                logging.warning("%s: broker symbol not found",base_symbol)
                continue
            try:
                b=bars(symbol,mt5.TIMEFRAME_M15)
                ts=int(b[-1]["time"])
                if last_bar.get(symbol)==ts:continue
                last_bar[symbol]=ts
                raw=evaluate_m15(base_symbol,symbol,b)
                if not raw:continue
                sig={"symbol":base_symbol,"brokerSymbol":symbol,"time":datetime.fromtimestamp(ts,timezone.utc).isoformat(),**raw}
                ok,reason=allowed(sig,cfg,envmap.get(base_symbol,{}))
                if ok:
                    eok,ereason=environment_allowed(sig,envmap.get(base_symbol,{}))
                    if not eok:ok,reason=False,ereason
                if ok and not runtime_ok:ok,reason=False,"RUNTIME_CACHE_STALE"
                enqueue_gas("saveEASignal",{"data":{"SignalTime":sig["time"],"Pair":base_symbol,"Direction":sig["direction"],"Rule":sig.get("rule","M15"),"P":sig.get("pattern",""),"MachineSignal":"ON","EntryStatus":"ENTRY" if ok else "SKIP","BlockReason":reason,"StrategyReason":sig.get("strategyReason",""),"Retracement":sig.get("retracement",""),"Q75":sig.get("q75",""),"Strength":sig.get("strength",""),"PairSnapshotJSON":json.dumps(envmap.get(base_symbol,{}),ensure_ascii=False,default=str),"EASettingSnapshotJSON":json.dumps((cfg.get("pairs") or {}).get(base_symbol,{}),ensure_ascii=False,default=str)}})
                if not ok:continue
                pc=(cfg.get("pairs") or {}).get(base_symbol,{})
                result=send_order({**sig,"symbol":symbol},pc,cfg)
                if not result.get("dry_run",False):
                    enqueue_gas("saveMT5Execution",{"data":{**account_snapshot(),"Source":"EA","Pair":base_symbol,"Direction":sig["direction"],"EntryTime":sig["time"],"EntryPrice":result.get("price",""),"Lot":result.get("volume",""),"Ticket":result.get("order",""),"Deal":result.get("deal",""),"SL":sig.get("sl","")}})
                logging.info("%s %s %s",symbol,sig["direction"],result)
            except Exception as e:
                logging.exception("%s failed",symbol)
                enqueue_gas("saveEAError",{"data":{"symbol":symbol,"error":str(e),"time":datetime.now(timezone.utc).isoformat()}})
        _stop.wait(POLL_SEC)

if __name__=="__main__":
    try:run()
    finally:
        _stop.set()
        mt5.shutdown()
