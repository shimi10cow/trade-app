"""Hybrid EA runner. Start with DRY_RUN=true. Windows + MT5 terminal + Python 3.11."""
import os,time,json,logging,threading,queue
from datetime import datetime,timezone
import requests
import MetaTrader5 as mt5
from m15_strategy import evaluate as evaluate_m15_strategy

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
ENV_MAX_STALE=7200

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
        cfg={"globalEntry":truth(app.get("globalEntry"),False),"pairs":{}}
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

def loss_for(symbol,direction,lot,entry,sl):
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

def send_order(sig,pc):
    symbol=sig["symbol"]
    if not mt5.symbol_select(symbol,True):raise RuntimeError(f"{symbol}: symbol_select failed")
    tick=mt5.symbol_info_tick(symbol)
    if not tick:raise RuntimeError(f"{symbol}: no tick")
    buy=sig["direction"].upper()=="BUY";price=tick.ask if buy else tick.bid
    if not price or price<=0:raise RuntimeError(f"{symbol}: market closed/no live price")
    if getattr(tick,"time",0) and time.time()-float(tick.time)>300:raise RuntimeError(f"{symbol}: stale tick")
    sl=float(sig["sl"])
    if (buy and sl>=price) or ((not buy) and sl<=price):raise RuntimeError(f"{symbol}: invalid SL side")
    lot=lot_for(symbol,sig["direction"],price,sl,pc)
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

def enqueue_gas(action,data):_outbox.put((action,data))

def outbox_worker():
    while not _stop.is_set():
        try:action,data=_outbox.get(timeout=1)
        except queue.Empty:continue
        try:gas_post(action,data)
        except Exception as e:
            logging.error("GAS outbox failed %s: %s",action,e)
            _stop.wait(5)
            if not _stop.is_set():_outbox.put((action,data))
        finally:_outbox.task_done()
def run():
    connect()
    refresh_runtime_once()
    threading.Thread(target=runtime_refresher,daemon=True).start()
    threading.Thread(target=outbox_worker,daemon=True).start()
    while True:
        cfg,envs,runtime_ok=cached_runtime()
        envmap={pair_name(x):x for x in envs if isinstance(x,dict) and pair_name(x)}
        targets=PAIR_OVERRIDE or list(envmap)
        for base_symbol in sorted(set(targets)):
            symbol=resolve_symbol(base_symbol)
            if not symbol:
                logging.warning("%s: broker symbol not found",base_symbol); continue
            try:
                b=bars(symbol,mt5.TIMEFRAME_M15)
                ts=int(b[-1]["time"])
                if last_bar.get(symbol)==ts:continue
                last_bar[symbol]=ts
                raw=evaluate_m15(base_symbol,symbol,b)
                if not raw:continue
                sig={"symbol":base_symbol,"brokerSymbol":symbol,"time":datetime.fromtimestamp(ts,timezone.utc).isoformat(),**raw}
                ok,reason=allowed(sig,cfg,envmap.get(base_symbol,{}))
                if ok and not runtime_ok:ok,reason=False,"RUNTIME_CACHE_STALE"
                enqueue_gas("saveEASignal",{"data":{"SignalTime":sig["time"],"Pair":base_symbol,"Direction":sig["direction"],"Rule":sig.get("rule","M15"),"P":sig.get("pattern",""),"MachineSignal":"ON","EntryStatus":"ENTRY" if ok else "SKIP","BlockReason":reason,"StrategyReason":sig.get("strategyReason",""),"Retracement":sig.get("retracement",""),"Q75":sig.get("q75",""),"Strength":sig.get("strength",""),"PairSnapshotJSON":json.dumps(envmap.get(base_symbol,{}),ensure_ascii=False,default=str),"EASettingSnapshotJSON":json.dumps((cfg.get("pairs") or {}).get(base_symbol,{}),ensure_ascii=False,default=str)}})
                if not ok:continue
                pc=(cfg.get("pairs") or {}).get(base_symbol,{})
                result=send_order({**sig,"symbol":symbol},pc)
                if not result.get("dry_run",False):
                    enqueue_gas("saveMT5Execution",{"data":{**account_snapshot(),"Source":"EA","Pair":base_symbol,"Direction":sig["direction"],"EntryTime":sig["time"],"EntryPrice":result.get("price",""),"Lot":result.get("volume",""),"Ticket":result.get("order",""),"Deal":result.get("deal","")}})
                logging.info("%s %s %s",symbol,sig["direction"],result)
            except Exception as e:
                logging.exception("%s failed",symbol)
                enqueue_gas("saveEAError",{"symbol":symbol,"error":str(e)})
        time.sleep(POLL_SEC)

if __name__=="__main__":
    try:run()
    finally:
        _stop.set()
        mt5.shutdown()
