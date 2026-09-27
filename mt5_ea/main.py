"""Hybrid EA runner. Start with DRY_RUN=true. Windows + MT5 terminal + Python 3.11."""
import time
import os,time,json,logging,threading,queue,sqlite3
from datetime import datetime,timezone,timedelta
import requests
import MetaTrader5 as mt5
from m15_strategy import evaluate as evaluate_m15_strategy, load_state as load_m15_state, register_execution as register_m15_execution, bootstrap as bootstrap_m15, collect_virtual_updates, recover_execution as recover_m15_execution, pip_size as m15_pip_size
from h1_strategy import evaluate as evaluate_h1_strategy, load_state as load_h1_state, register_execution as register_h1_execution
import telegram_notify as telegram

DEFAULT_GAS_URL="https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
GAS_URL=os.getenv("EA_GAS_URL",DEFAULT_GAS_URL)
DRY_RUN=os.getenv("EA_DRY_RUN","true").lower()=="true"
POLL_SEC=int(os.getenv("EA_POLL_SEC","2"))
MAGIC=int(os.getenv("EA_MAGIC","560001"))
PAIR_OVERRIDE=[x.strip() for x in os.getenv("EA_PAIRS","").split(",") if x.strip()]
LIVE_LOGIN=os.getenv("EA_LIVE_LOGIN","").strip()
LIVE_SERVER=os.getenv("EA_LIVE_SERVER","").strip()
LIVE_ARMED=os.getenv("EA_LIVE_ARMED","false").lower()=="true"
MAX_SIGNAL_AGE_SEC=int(os.getenv("EA_MAX_SIGNAL_AGE_SEC","1200"))
CONTROL_FETCH_SEC=max(3,int(os.getenv("EA_CONTROL_FETCH_SEC","10")))
LIVE_REQUIRE_REAL=os.getenv("EA_LIVE_REQUIRE_REAL","true").lower()=="true"
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
last_bar={}
_symbol_cache={}
_cache={"settings":None,"settings_at":0.0,"env":None,"env_at":0.0}
_cache_lock=threading.Lock()
_stop=threading.Event()
_outbox=queue.Queue()
SETTINGS_MAX_STALE=900
ENV_MAX_STALE=7200
ENV_FETCH_SEC=60
RUNTIME_CACHE_FILE=os.path.join(os.path.dirname(__file__),"runtime_cache.json")
OUTBOX_DB=os.getenv("EA_OUTBOX_DB",os.path.join(os.path.dirname(__file__),"ea_outbox.sqlite3"))

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

def live_safety_check():
    """Fail closed before any real order can be sent."""
    if DRY_RUN:return True
    if not LIVE_ARMED:raise RuntimeError("LIVE_NOT_ARMED")
    if not LIVE_LOGIN or not LIVE_SERVER:raise RuntimeError("LIVE_ACCOUNT_LOCK_NOT_CONFIGURED")
    a=mt5.account_info(); t=mt5.terminal_info()
    if not a or not t:raise RuntimeError("LIVE_ACCOUNT_OR_TERMINAL_UNAVAILABLE")
    if str(a.login)!=LIVE_LOGIN or str(a.server)!=LIVE_SERVER:raise RuntimeError("LIVE_ACCOUNT_LOCK_MISMATCH")
    if LIVE_REQUIRE_REAL and getattr(a,"trade_mode",None)!=mt5.ACCOUNT_TRADE_MODE_REAL:raise RuntimeError("LIVE_ACCOUNT_NOT_REAL")
    if float(getattr(a,"equity",0) or 0)<=0:raise RuntimeError("LIVE_EQUITY_NOT_POSITIVE")
    if not bool(getattr(a,"trade_allowed",False)):raise RuntimeError("ACCOUNT_TRADE_NOT_ALLOWED")
    if not bool(getattr(t,"trade_allowed",False)):raise RuntimeError("TERMINAL_TRADE_NOT_ALLOWED")
    if not bool(getattr(t,"connected",False)):raise RuntimeError("TERMINAL_NOT_CONNECTED")
    if not bool(getattr(t,"dlls_allowed",True)):raise RuntimeError("TERMINAL_DLLS_NOT_ALLOWED")
    return True

def bars(symbol,tf,count=3000):
    rates=mt5.copy_rates_from_pos(symbol,tf,0,count)
    if rates is None or len(rates)<3:raise RuntimeError(f"{symbol}: insufficient rates")
    # Drop bar 0: it is still forming. All decisions use closed candles only.
    return rates[:-1]

def latest_closed_bar_time(symbol):
    r=mt5.copy_rates_from_pos(symbol,mt5.TIMEFRAME_M15,1,1)
    return int(r[0]["time"]) if r is not None and len(r) else 0

def bars_since(symbol,last_time,count=3000):
    """Return closed M15 history once; caller replays every missing closed bar causally."""
    b=bars(symbol,mt5.TIMEFRAME_M15,count)
    if not last_time:return b,[len(b)]
    ends=[i+1 for i,r in enumerate(b) if int(r["time"])>int(last_time)]
    return b,ends

def evaluate_missing_m15(base_symbol,broker_symbol):
    state=load_m15_state(); last=int(((state.get("pairs") or {}).get(base_symbol) or {}).get("last_time",0))
    b,ends=bars_since(broker_symbol,last)
    if not ends:return []
    tick=mt5.symbol_info_tick(broker_symbol)
    spread=max(0.0,float(tick.ask)-float(tick.bid)) if tick and tick.ask and tick.bid else 0.0
    out=[]
    # Each missing bar is replayed in chronological order. This preserves all intermediate
    # Stoch/P-count/ledger transitions after PC downtime.
    for end in ends:
        r=evaluate_m15_strategy(base_symbol,b[:end],spread)
        if r is not None:
            r["spreadPrice"]=spread; r["_bar_time"]=int(b[end-1]["time"]); out.append(r)
    return out

def evaluate_missing_h1(base_symbol,broker_symbol):
    state=load_h1_state(); last=int(((state.get("pairs") or {}).get(base_symbol) or {}).get("last_h1_time",0))
    b=bars(broker_symbol,mt5.TIMEFRAME_M15,3000)
    tick=mt5.symbol_info_tick(broker_symbol)
    spread=max(0.0,float(tick.ask)-float(tick.bid)) if tick and tick.ask and tick.bid else 0.0
    out=[]
    # Replay only completed H1 boundaries (:45 M15 close) after the persisted H1 cursor.
    for end in range(4,len(b)+1):
        bt=int(b[end-1]["time"])
        if ((bt%3600)//60)!=45 or bt//3600<=last//3600:continue
        r=evaluate_h1_strategy(base_symbol,b[:end],spread)
        if r is not None:
            r["spreadPrice"]=spread;r["_bar_time"]=bt;out.append(r)
    return out

def pair_name(x):
    return str(x.get("PairName（元）") or x.get("PairName") or x.get("Pair") or x.get("通貨ペア") or x.get("pair") or "").strip() if isinstance(x,dict) else ""

def resolve_symbol(base):
    """Map logical symbols to the exact XM KIWAMI instruments; never fall back to Standard."""
    if base in _symbol_cache:return _symbol_cache[base]
    b="".join(c for c in str(base).upper() if c.isalnum())
    target="GOLD#" if b=="XAUUSD" else (b+"#" if len(b)==6 and b.isalpha() else None)
    found=target if target and mt5.symbol_info(target) else None
    _symbol_cache[base]=found
    return found

def truth(v,default=False):
    if v is None or v=="": return default
    return str(v).strip().lower() in ("1","true","on","yes","有効","on（有効）")

def pair_settings():
    """Normalize the existing Trade Tracker EA_Settings/App_Settings contract."""
    try:
        hybrid=gas_get("getHybridConfig") or {}
        rows=hybrid.get("settings") or []
        app=hybrid.get("appSettings") or {}
        if isinstance(app,list): app={str(x.get("Key")):x.get("Value") for x in app if isinstance(x,dict) and x.get("Key")}
        cfg={"globalEntry":truth(app.get("globalEntry"),False),"envRefreshMin":float(app.get("envRefreshMin") or 60),"settingsRefreshMin":float(app.get("settingsRefreshMin") or 5),"totalRiskCapEnabled":truth(app.get("totalRiskCapEnabled") or app.get("総同時Risk上限ON"),False),"totalRiskCap":float(app.get("totalRiskCap") or app.get("総同時Risk上限%") or 0),"notifySignal":truth(app.get("notifySignal"),True),"notifyEntry":truth(app.get("notifyEntry"),True),"notifyExit":truth(app.get("notifyExit"),True),"notifyError":truth(app.get("notifyError"),True),"pairs":{}}
        for r in rows if isinstance(rows,list) else []:
            p=pair_name(r)
            if not p: continue
            mode=str(r.get("稼働方法") or "stop").strip().lower()
            if mode in ("自動","自動売買","auto"): mode="auto"
            elif mode in ("signal","signal-only","シグナルのみ"): mode="signal"
            else: mode="stop"
            cfg["pairs"][p]={
                "mode":mode,
                "direction":r.get("許可方向") or "Both",
                "m15":truth(r.get("M15"),True),
                "h1":truth(r.get("H1"),False),
                "riskType":"fixedLot" if str(r.get("Lot方式") or "").strip() in ("固定Lot","fixedLot") else ("fixedLoss" if str(r.get("Lot方式") or "").strip() in ("固定損失額","fixedLoss") else "riskPercent"),
                "riskValue":float(r.get("Lot値") or 0.01),
                "riskCapEnabled":truth(r.get("Risk上限ON"),True),
                "riskCap":float(r.get("Risk上限%") or 1),
                "autoExit":str(r.get("決済方法") or "auto").lower() not in ("off","manual","裁量","手動決済")
            }
        # A missing EA_Settings row must never enable trading. Keep requested test pairs
        # visible in DRY RUN as explicit STOP defaults so market-data/strategy checks can run.
        for p in PAIR_OVERRIDE:
            cfg["pairs"].setdefault(p,{"mode":"stop","direction":"Both","m15":True,"h1":False,
                "riskType":"fixedLot","riskValue":0.01,"riskCapEnabled":True,"riskCap":1.0,"autoExit":True})
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
    result=evaluate_m15_strategy(base_symbol,closed_bars,spread)
    if result is not None:result["spreadPrice"]=spread
    return result

def allowed(sig,cfg,env,timeframe="M15"):
    if not sig:return False,"NO_SIGNAL"
    if not sig.get("strategyAllowed",False):return False,sig.get("strategyReason","STRATEGY_REJECT")
    if not cfg.get("globalEntry",False):return False,"GLOBAL_STOP"
    pc=(cfg.get("pairs") or {}).get(sig["symbol"],{})
    mode=pc.get("mode","stop")
    if mode=="stop":return False,"PAIR_STOP"
    if mode=="signal":return False,"SIGNAL_ONLY"
    if mode!="auto":return False,"INVALID_MODE"
    if timeframe=="M15" and not pc.get("m15",True):return False,"M15_OFF"
    if timeframe=="H1" and not pc.get("h1",False):return False,"H1_OFF"
    d=str(pc.get("direction","Both")).upper()
    if d not in ("BOTH","両方",sig["direction"].upper()):return False,"DIRECTION_BLOCK"
    return True,"OK"


def env_value(env,*keys):
    for k in keys:
        if k in env and env.get(k) not in (None,""):return env.get(k)
    return None

def environment_allowed(sig,env,max_age_minutes=60):
    if not isinstance(env,dict) or not env:return False,"ENV_MISSING"
    stamp=env_value(env,"EA環境確認日時","環境確認日時","確認日時","更新日時","EnvironmentConfirmedAt","confirmedAt","updatedAt")
    if not stamp:return False,"ENV_TIME_MISSING"
    if stamp:
        try:
            raw=str(stamp).strip()
            try:dt=datetime.fromisoformat(raw.replace("Z","+00:00"))
            except ValueError:dt=datetime.strptime(raw,"%Y/%m/%d %H:%M")
            if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone(timedelta(hours=9)))
            if (datetime.now(timezone.utc)-dt.astimezone(timezone.utc)).total_seconds()>float(max_age_minutes)*60:return False,"ENV_EXPIRED"
        except Exception:return False,"ENV_TIME_INVALID"
    push=str(env_value(env,"TL\u63a8\u9032\u74b0\u5883","TL 推進","TL推進","TL_推進") or "").upper()
    counter=str(env_value(env,"TL\u9006\u30c8\u30ec\u74b0\u5883","TL 逆トレ","TL逆トレ","TL_逆トレ") or "").upper()
    dm={chr(8593):"BUY","UP":"BUY","BUY":"BUY",chr(8595):"SELL","DOWN":"SELL","SELL":"SELL"}
    dirs={dm.get(push,push),dm.get(counter,counter)}
    dirs.discard("");dirs.discard("NONE");dirs.discard("\u306a\u3057");dirs.discard("N/A");dirs.discard("-")
    if dirs and sig["direction"].upper() not in dirs:return False,"ENV_DIRECTION_BLOCK"
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
    live_safety_check()
    req={"action":mt5.TRADE_ACTION_SLTP,"position":position.ticket,"symbol":position.symbol,"sl":float(new_sl),"tp":float(position.tp or 0),"magic":MAGIC}
    r=mt5.order_send(req)
    return bool(r and r.retcode==mt5.TRADE_RETCODE_DONE)

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

def notify_signal(sig,cfg):
    telegram.send("signal",f"EA SIGNAL\nPair: {sig.get('symbol')}\nTF: {sig.get('timeframe','M15')}\nDirection: {sig.get('direction')}\nPattern: {sig.get('pattern','')}\nPrice: {sig.get('entry','')}\nSL: {sig.get('sl','')}\nTime: {sig.get('time','')}",cfg)

def notify_entry(sig,result,cfg):
    telegram.send("entry",f"EA ENTRY\nPair: {sig.get('symbol')}\nTF: {sig.get('timeframe','M15')}\nDirection: {sig.get('direction')}\nPrice: {result.get('price','')}\nLot: {result.get('volume','')}\nSL: {result.get('sl',sig.get('sl',''))}\nPattern: {sig.get('pattern','')}\nTime: {sig.get('time','')}",cfg)

def notify_exit(base,t,cfg):
    telegram.send("exit",f"EA EXIT\nPair: {base}\nDirection: {t.get('direction','')}\nPattern: {t.get('pattern','')}\nEntry: {t.get('entry','')}\nExit: {t.get('exit','')}\nR: {t.get('final_r','')}",cfg)

def account_snapshot():
    a=mt5.account_info()
    return {"Account":str(a.login) if a else "","Server":str(a.server) if a else "","AccountMode":"DEMO" if a and getattr(a,"trade_mode",None)==mt5.ACCOUNT_TRADE_MODE_DEMO else "REAL" if a else ""}

def validate_live_pair_config(pc):
    if DRY_RUN:return True
    if not isinstance(pc,dict) or pc.get("mode")!="auto":raise RuntimeError("LIVE_PAIR_NOT_AUTO")
    method=pc.get("riskType")
    value=float(pc.get("riskValue",0) or 0)
    if method not in ("fixedLot","fixedLoss","riskPercent") or value<=0:raise RuntimeError("LIVE_RISK_CONFIG_INVALID")
    if pc.get("riskCapEnabled",True) and float(pc.get("riskCap",0) or 0)<=0:raise RuntimeError("LIVE_RISK_CAP_INVALID")
    return True

def send_order(sig,pc,cfg=None):
    live_safety_check()
    validate_live_pair_config(pc)
    symbol=sig["symbol"]
    if not mt5.symbol_select(symbol,True):raise RuntimeError(f"{symbol}: symbol_select failed")
    current=[p for p in (mt5.positions_get(symbol=symbol) or []) if int(getattr(p,"magic",0))==MAGIC]
    if len(current)>=2:raise RuntimeError("MAX_POSITIONS")
    tick=mt5.symbol_info_tick(symbol)
    if not tick:raise RuntimeError(f"{symbol}: no tick")
    info=mt5.symbol_info(symbol)
    if not info:raise RuntimeError(f"{symbol}: symbol_info unavailable")
    trade_mode=int(getattr(info,"trade_mode",mt5.SYMBOL_TRADE_MODE_DISABLED))
    if trade_mode==mt5.SYMBOL_TRADE_MODE_DISABLED:raise RuntimeError(f"{symbol}: trading disabled")
    buy=sig["direction"].upper()=="BUY";price=tick.ask if buy else tick.bid
    if not price or price<=0:raise RuntimeError(f"{symbol}: market closed/no live price")
    if not getattr(tick,"time",0) or time.time()-float(tick.time)>300:raise RuntimeError(f"{symbol}: stale tick")
    sl=float(sig["sl"])
    if (buy and sl>=price) or ((not buy) and sl<=price):raise RuntimeError(f"{symbol}: invalid SL side")
    lot=lot_for(symbol,sig["direction"],price,sl,pc)
    if cfg is not None and not total_risk_allowed(symbol,sig["direction"],lot,price,sl,cfg):raise RuntimeError("TOTAL_RISK_CAP")
    point=float(info.point or 0)
    min_stop=float(getattr(info,"trade_stops_level",0) or 0)*point
    if min_stop>0 and abs(price-sl)<min_stop:raise RuntimeError(f"{symbol}: BROKER_STOPS_LEVEL")
    base_req={"action":mt5.TRADE_ACTION_DEAL,"symbol":symbol,"volume":lot,
         "type":mt5.ORDER_TYPE_BUY if buy else mt5.ORDER_TYPE_SELL,
         "price":price,"sl":sl,"deviation":20,"magic":MAGIC,
         "comment":("HybridEA-H1" if str(sig.get("timeframe","M15")).upper()=="H1" else "HybridEA-M15"),"type_time":mt5.ORDER_TIME_GTC}
    if sig.get("tp"):base_req["tp"]=float(sig["tp"])
    # Broker filling modes vary by symbol/account. Pick the first mode accepted by order_check.
    req=None; check=None
    candidates=[]
    fm=int(getattr(info,"filling_mode",0) or 0)
    for mode in (fm,mt5.ORDER_FILLING_FOK,mt5.ORDER_FILLING_IOC,mt5.ORDER_FILLING_RETURN):
        if mode not in candidates:candidates.append(mode)
    for mode in candidates:
        candidate={**base_req,"type_filling":mode}
        c=mt5.order_check(candidate)
        if c is not None and int(getattr(c,"retcode",0) or 0)==0:
            req,check=candidate,c;break
    if req is None:raise RuntimeError(f"order_check rejected all filling modes: {check or mt5.last_error()}")
    if DRY_RUN:return {"dry_run":True,"request":req,"order_check":str(check),"spread":max(0.0,float(tick.ask)-float(tick.bid)),"sl":sl}
    before={int(p.ticket) for p in (mt5.positions_get(symbol=symbol) or []) if int(getattr(p,"magic",0))==MAGIC}
    res=mt5.order_send(req)
    if res is None or res.retcode!=mt5.TRADE_RETCODE_DONE:raise RuntimeError(f"order_send failed: {res}")
    position_ticket=None
    for _ in range(10):
        candidates=[p for p in (mt5.positions_get(symbol=symbol) or []) if int(getattr(p,"magic",0))==MAGIC and int(p.ticket) not in before and ((buy and p.type==mt5.POSITION_TYPE_BUY) or ((not buy) and p.type==mt5.POSITION_TYPE_SELL))]
        if candidates:
            position_ticket=max(candidates,key=lambda p:getattr(p,"time_msc",getattr(p,"time",0))).ticket;break
        time.sleep(0.1)
    return {"dry_run":False,"order":res.order,"deal":res.deal,"ticket":position_ticket or res.order,"price":res.price,"volume":res.volume,"spread":max(0.0,float(tick.ask)-float(tick.bid)),"sl":sl}

def manage_ea_positions(cfg=None):
    """Keep EA-created MT5 SLs aligned with the strategy ledger even while new entries are stopped."""
    state=load_m15_state()
    all_positions=[p for p in (mt5.positions_get() or []) if int(getattr(p,"magic",0))==MAGIC]
    if not all_positions:return
    for base,ps in (state.get("pairs") or {}).items():
        pc=((cfg or {}).get("pairs") or {}).get(base,{})
        if cfg is not None and not pc.get("autoExit",True):continue
        symbol=resolve_symbol(base)
        if not symbol:continue
        positions=[p for p in all_positions if getattr(p,"symbol","")==symbol]
        positions.sort(key=lambda p:getattr(p,"time",0))
        known={str(t.get("ticket","")) for t in (ps.get("trades") or {}).values()}
        for p in positions:
            if str(p.ticket) not in known and float(getattr(p,"sl",0) or 0)>0:
                recover_m15_execution(base,"BUY" if p.type==mt5.POSITION_TYPE_BUY else "SELL",float(p.price_open),float(p.sl),int(getattr(p,"time",time.time())),p.ticket)
        if positions:
            ps=(load_m15_state().get("pairs") or {}).get(base,ps)
        trades=[t for t in (ps.get("trades") or {}).values() if t.get("entered") and t.get("open")]
        by_ticket={str(t.get("ticket")):t for t in trades if t.get("ticket") not in (None,"")}
        for p in positions:
            t=by_ticket.get(str(p.ticket))
            if not t:
                logging.error("%s: no strategy ledger match for MT5 position ticket=%s; SL unchanged",base,p.ticket)
                continue
            target=float(t.get("sl") or 0)
            current=float(getattr(p,"sl",0) or 0)
            buy=p.type==mt5.POSITION_TYPE_BUY
            improve=target>0 and (current<=0 or (buy and target>current) or ((not buy) and target<current))
            if improve and modify_position_sl(p,target):
                enqueue_gas("saveMT5Execution",{"data":{**account_snapshot(),"Source":"EA","Pair":base,"Direction":"BUY" if buy else "SELL","Ticket":p.ticket,"Event":"SL_UPDATE","SL":target,"EventTime":datetime.now(timezone.utc).isoformat()}})

def refresh_global_control():
    """Refresh the app-level start/stop switch independently of full settings."""
    try:
        app=gas_get("getAppSettings") or {}
        if isinstance(app,list):
            app={str(x.get("Key")):x.get("Value") for x in app if isinstance(x,dict) and x.get("Key")}
        if not isinstance(app,dict):return False
        with _cache_lock:
            settings=_cache.get("settings")
            if not isinstance(settings,dict):return False
            settings["globalEntry"]=truth(app.get("globalEntry"),False)
            settings["notifySignal"]=truth(app.get("notifySignal"),settings.get("notifySignal",True))
            settings["notifyEntry"]=truth(app.get("notifyEntry"),settings.get("notifyEntry",True))
            settings["notifyExit"]=truth(app.get("notifyExit"),settings.get("notifyExit",True))
            settings["notifyError"]=truth(app.get("notifyError"),settings.get("notifyError",True))
        return True
    except Exception as e:
        logging.error("global EA control fetch failed: %s",e)
        return False

def refresh_runtime_once():
    now=time.time(); settings=pair_settings(); env=environment()
    with _cache_lock:
        if settings is not None:_cache["settings"],_cache["settings_at"]=settings,now
        if env is not None:_cache["env"],_cache["env_at"]=env,now
    save_runtime_disk_cache()

def runtime_refresher():
    last_control=0.0
    while not _stop.is_set():
        now=time.time()
        with _cache_lock:
            current=_cache["settings"] or {}
            settings_interval=max(30.0,float(current.get("settingsRefreshMin",5) or 5)*60.0)
            need_s=_cache["settings"] is None or now-_cache["settings_at"]>=settings_interval
            need_e=_cache["env"] is None or now-_cache["env_at"]>=ENV_FETCH_SEC
        if now-last_control>=CONTROL_FETCH_SEC:
            refresh_global_control();last_control=time.time()
        if need_s:
            x=pair_settings()
            if x is not None:
                with _cache_lock:_cache["settings"],_cache["settings_at"]=x,time.time()
        if need_e:
            x=environment()
            if x is not None:
                with _cache_lock:_cache["env"],_cache["env_at"]=x,time.time()
        _stop.wait(2)

def load_runtime_disk_cache():
    try:
        x=json.load(open(RUNTIME_CACHE_FILE,"r",encoding="utf-8"))
        with _cache_lock:
            _cache["settings"]=x.get("settings"); _cache["settings_at"]=float(x.get("settings_at") or 0)
            _cache["env"]=x.get("env"); _cache["env_at"]=float(x.get("env_at") or 0)
        return _cache["settings"] is not None
    except Exception:return False

def save_runtime_disk_cache():
    try:
        with _cache_lock:x={k:_cache[k] for k in ("settings","settings_at","env","env_at")}
        with open(RUNTIME_CACHE_FILE,"w",encoding="utf-8") as fh:json.dump(x,fh,ensure_ascii=False)
    except Exception as e:logging.warning("runtime cache save failed: %s",e)

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
        db.execute("CREATE TABLE IF NOT EXISTS outbox(id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, next_attempt REAL NOT NULL DEFAULT 0, last_error TEXT NOT NULL DEFAULT '')")
        cols={r[1] for r in db.execute("PRAGMA table_info(outbox)")}
        for name,ddl in (("attempts","INTEGER NOT NULL DEFAULT 0"),("next_attempt","REAL NOT NULL DEFAULT 0"),("last_error","TEXT NOT NULL DEFAULT ''")):
            if name not in cols:db.execute(f"ALTER TABLE outbox ADD COLUMN {name} {ddl}")
        db.commit()

def enqueue_gas(action,data):
    with sqlite3.connect(OUTBOX_DB) as db:
        db.execute("INSERT INTO outbox(action,payload,created,next_attempt) VALUES(?,?,?,?)",(action,json.dumps(data,ensure_ascii=False,default=str),time.time(),0))
        db.commit()

def outbox_worker():
    while not _stop.is_set():
        try:
            now=time.time()
            with sqlite3.connect(OUTBOX_DB) as db:
                row=db.execute("SELECT id,action,payload,attempts FROM outbox WHERE next_attempt<=? ORDER BY id LIMIT 1",(now,)).fetchone()
            if not row:_stop.wait(1);continue
            oid,action,payload,attempts=row
            gas_post(action,json.loads(payload))
            with sqlite3.connect(OUTBOX_DB) as db:
                db.execute("DELETE FROM outbox WHERE id=?",(oid,));db.commit()
        except Exception as e:
            logging.error("GAS outbox failed: %s",e)
            try:
                delay=min(300,2**min(int(attempts or 0),8))
                with sqlite3.connect(OUTBOX_DB) as db:
                    db.execute("UPDATE outbox SET attempts=attempts+1,next_attempt=?,last_error=? WHERE id=?",(time.time()+delay,str(e)[:1000],oid));db.commit()
            except Exception:pass
            _stop.wait(1)

def signal_id(base,ts,pattern,direction,timeframe="M15"):
    return f"EA-{str(timeframe).upper()}-{base}-{int(ts)}-{pattern}-{direction}"

def save_virtual_exits(base,cfg):
    for t in collect_virtual_updates(base):
        tid=signal_id(base,t.get("entry_time",0),t.get("pattern",""),t.get("direction",""))
        enqueue_gas("saveEASignal",{"data":{"SignalID":tid,"ExitTime":datetime.fromtimestamp(int(t.get("exit_time",0)),timezone.utc).isoformat() if t.get("exit_time") else "",
            "ExitPrice":t.get("exit",""),"Pips":((float(t.get("exit",0))-float(t.get("entry",0)))*(1 if t.get("direction")=="BUY" else -1)/m15_pip_size(base)) if t.get("exit") is not None else "","R":t.get("final_r","")}})
        if t.get("entered"):notify_exit(base,t,cfg)

def bootstrap_missing_state(cfg):
    t0=time.perf_counter()
    logging.info("startup: checking strategy state")
    state=load_m15_state(); existing=state.get("pairs") or {}
    for base in sorted((cfg.get("pairs") or {}).keys()):
        if base in existing and int(existing[base].get("last_time",0))>0:continue
        symbol=resolve_symbol(base)
        if not symbol:continue
        tb=time.perf_counter()
        logging.info("%s: loading bootstrap M15 history",base)
        b=bars(symbol,mt5.TIMEFRAME_M15,3000)
        logging.info("%s: loaded %s closed M15 bars in %.2fs",base,len(b),time.perf_counter()-tb)
        tick=mt5.symbol_info_tick(symbol)
        spread=max(0.0,float(tick.ask)-float(tick.bid)) if tick and tick.ask and tick.bid else 0.0
        logging.info("%s: bootstrapping strategy state from %s closed M15 bars",base,len(b))
        bootstrap_m15(base,b,spread)
        logging.info("%s: bootstrap complete in %.2fs",base,time.perf_counter()-tb)
    logging.info("startup: strategy state ready in %.2fs",time.perf_counter()-t0)

def process_signal(base_symbol,symbol,raw,ts,cfg,envmap,runtime_ok,timeframe):
    sig_ts=int(raw.pop("_bar_time",ts)); tf=str(timeframe).upper()
    sig={"symbol":base_symbol,"brokerSymbol":symbol,"timeframe":tf,"time":datetime.fromtimestamp(sig_ts,timezone.utc).isoformat(),**raw}
    sid=signal_id(base_symbol,sig_ts,sig.get("pattern",""),sig["direction"],tf)
    if sig_ts!=ts or time.time()-sig_ts>MAX_SIGNAL_AGE_SEC:
        enqueue_gas("saveEASignal",{"data":{"SignalID":sid,"SignalTime":sig["time"],"Pair":base_symbol,"Direction":sig["direction"],"Rule":sig.get("rule",tf),"Pullback":sig.get("pattern",""),"Executed":"NO","SkipReason":"OFFLINE_CATCHUP","EntryPrice":sig.get("entry",""),"InitialSL":sig.get("sl","")}})
        return
    # Signal monitoring is independent from order permission. A user may keep the EA
    # globally stopped while receiving valid strategy signals via Telegram.
    strategy_signal=bool(sig.get("strategyAllowed",False))
    if strategy_signal:
        notify_signal(sig,cfg)
    ok,reason=allowed(sig,cfg,envmap.get(base_symbol,{}),tf)
    if ok:
        eok,ereason=environment_allowed(sig,envmap.get(base_symbol,{}),cfg.get("envRefreshMin",60))
        if not eok:ok,reason=False,ereason
    if ok and not runtime_ok:ok,reason=False,"RUNTIME_CACHE_STALE"
    enqueue_gas("saveEASignal",{"data":{"SignalID":sid,"SignalTime":sig["time"],"Pair":base_symbol,"Direction":sig["direction"],"Rule":sig.get("rule",tf),"Pullback":sig.get("pattern",""),"Executed":"DRY_RUN" if ok and DRY_RUN else ("YES" if ok else "NO"),"SkipReason":reason if not ok else "","EntryPrice":sig.get("entry",""),"InitialSL":sig.get("sl","")}})
    if not ok:return
    pc=(cfg.get("pairs") or {}).get(base_symbol,{})
    result=send_order({**sig,"symbol":symbol},pc,cfg)
    if not result.get("dry_run",False):
        if tf=="H1":
            register_h1_execution(base_symbol,sig.get("pattern",""),sig["direction"],result.get("price"),result.get("sl",sig["sl"]),sig_ts,result.get("spread",0.0),result.get("ticket"),result.get("deal"))
            recover_m15_execution(base_symbol,sig["direction"],result.get("price"),result.get("sl",sig["sl"]),sig_ts,result.get("ticket"))
        else:
            register_m15_execution(base_symbol,sig.get("pattern",""),sig["direction"],result.get("price"),result.get("sl",sig["sl"]),sig_ts,result.get("spread",0.0),result.get("ticket"),result.get("deal"))
        enqueue_gas("saveMT5Execution",{"data":{**account_snapshot(),"SignalID":sid,"Source":"EA-H1" if tf=="H1" else "EA","Pair":base_symbol,"Direction":sig["direction"],"EntryTime":sig["time"],"EntryPrice":result.get("price",""),"Lot":result.get("volume",""),"Ticket":result.get("ticket",""),"Deal":result.get("deal",""),"SL":sig.get("sl","")}})
        notify_entry(sig,result,cfg)
    logging.info("%s %s %s %s",symbol,tf,sig["direction"],result)

def run():
    connect()
    init_outbox()
    cached=load_runtime_disk_cache()
    cfg0,_,_=cached_runtime()
    bootstrap_missing_state(cfg0)
    startup_state=load_m15_state(); startup_pairs=(startup_state.get("pairs") or {})
    startup_targets=(set(PAIR_OVERRIDE)&set(startup_pairs)) if PAIR_OVERRIDE else set(startup_pairs)
    for base in startup_targets:
        ps=startup_pairs[base];sym=resolve_symbol(base)
        if sym and int(ps.get("last_time",0))>0:last_bar[sym]=int(ps["last_time"])
    logging.info("EA monitoring started; %s strategy cursors restored",len(last_bar))
    threading.Thread(target=runtime_refresher,daemon=True).start()
    threading.Thread(target=outbox_worker,daemon=True).start()
    while not _stop.is_set():
        cfg,envs,runtime_ok=cached_runtime()
        envmap={pair_name(x):x for x in envs if isinstance(x,dict) and pair_name(x)}
        configured=set((cfg.get("pairs") or {}).keys())
        targets=(set(PAIR_OVERRIDE)&configured) if PAIR_OVERRIDE else configured
        manage_ea_positions(cfg)
        for base_symbol in sorted(targets):
            symbol=resolve_symbol(base_symbol)
            if not symbol:continue
            try:
                ts=latest_closed_bar_time(symbol)
                if not ts or last_bar.get(symbol)==ts:continue
                results=evaluate_missing_m15(base_symbol,symbol)
                last_bar[symbol]=ts
                save_virtual_exits(base_symbol,cfg)
                if results:process_signal(base_symbol,symbol,results[-1],ts,cfg,envmap,runtime_ok,"M15")
                pc=(cfg.get("pairs") or {}).get(base_symbol,{})
                if pc.get("h1",False) and ((ts%3600)//60)==45:
                    h1_results=evaluate_missing_h1(base_symbol,symbol)
                    if h1_results:process_signal(base_symbol,symbol,h1_results[-1],ts,cfg,envmap,runtime_ok,"H1")
            except Exception as e:
                logging.exception("%s failed",symbol)
                enqueue_gas("saveEAError",{"data":{"symbol":symbol,"error":str(e),"time":datetime.now(timezone.utc).isoformat()}})
                telegram.error(f"EA ERROR\nPair: {base_symbol}\nError: {e}",cfg,key=f"{base_symbol}:{type(e).__name__}:{e}")
        _stop.wait(POLL_SEC)

if __name__=="__main__":
    try:run()
    finally:
        _stop.set()
        mt5.shutdown()
