"""Hybrid EA runner. Start with DRY_RUN=true. Windows + MT5 terminal + Python 3.11."""
import os,time,json,logging
from datetime import datetime,timezone
import requests
import MetaTrader5 as mt5

GAS_URL=os.getenv("EA_GAS_URL","")
DRY_RUN=os.getenv("EA_DRY_RUN","true").lower()=="true"
POLL_SEC=int(os.getenv("EA_POLL_SEC","2"))
MAGIC=int(os.getenv("EA_MAGIC","560001"))
PAIR_OVERRIDE=[x.strip() for x in os.getenv("EA_PAIRS","").split(",") if x.strip()]
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
last_bar={}

def gas_get(action,**params):
    if not GAS_URL:return {}
    r=requests.get(GAS_URL,params={"action":action,**params},timeout=10);r.raise_for_status()
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

def bars(symbol,tf,count=700):
    rates=mt5.copy_rates_from_pos(symbol,tf,0,count)
    if rates is None or len(rates)<3:raise RuntimeError(f"{symbol}: insufficient rates")
    # Drop bar 0: it is still forming. All decisions use closed candles only.
    return rates[:-1]

def pair_name(x):
    return str(x.get("Pair") or x.get("PairName") or x.get("通貨ペア") or x.get("pair") or "").strip() if isinstance(x,dict) else ""

def resolve_symbol(base):
    if mt5.symbol_info(base): return base
    b="".join(c for c in base.upper() if c.isalnum())
    aliases=[b]+(["GOLD"] if b=="XAUUSD" else [])
    hits=[x.name for x in (mt5.symbols_get() or []) if any(a in "".join(c for c in x.name.upper() if c.isalnum()) for a in aliases)]
    hits.sort(key=lambda n:(0 if "".join(c for c in n.upper() if c.isalnum()).startswith(b) else 1,len(n)))
    return hits[0] if hits else None

def pair_settings():
    try:return gas_get("getEASettings") or {}
    except Exception as e:
        logging.error("settings fetch failed: %s",e);return {}

def environment():
    try:return gas_get("getPairs") or []
    except Exception as e:
        logging.error("environment fetch failed: %s",e);return []

def evaluate_m15(symbol,closed_bars,settings,env):
    """ONLY strategy adapter. Return None or a dict like:
    {"direction":"BUY","pattern":"P2","entry":1.0,"sl":0.9,"tp":None,"reason":"..."}
    Insert the already-backtested M15 rule here; never use the forming candle.
    """
    return None

def allowed(sig,cfg,env):
    if not sig:return False,"NO_SIGNAL"
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

def send_order(sig,pc):
    symbol=sig["symbol"]
    if not mt5.symbol_select(symbol,True):raise RuntimeError(f"{symbol}: symbol_select failed")
    tick=mt5.symbol_info_tick(symbol)
    if not tick:raise RuntimeError(f"{symbol}: no tick")
    buy=sig["direction"].upper()=="BUY";price=tick.ask if buy else tick.bid
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

def run():
    connect()
    while True:
        cfg=pair_settings();envs=environment()
        envmap={str(x.get("Pair") or x.get("PairName") or x.get("通貨ペア") or ""):x for x in envs if isinstance(x,dict)}
        targets=PAIR_OVERRIDE or [pair_name(x) for x in envs if pair_name(x)]
        for base_symbol in sorted(set(targets)):
            symbol=resolve_symbol(base_symbol)
            if not symbol:
                logging.warning("%s: broker symbol not found",base_symbol)
                continue
            try:
                b=bars(symbol,mt5.TIMEFRAME_M15)
                ts=int(b[-1]["time"])
                if last_bar.get(symbol)==ts:continue
                last_bar[symbol]=ts
                raw=evaluate_m15(base_symbol,b,cfg,envmap.get(base_symbol,{}))
                if not raw:continue
                sig={"symbol":base_symbol,"brokerSymbol":symbol,"time":datetime.fromtimestamp(ts,timezone.utc).isoformat(),**raw}
                ok,reason=allowed(sig,cfg,envmap.get(base_symbol,{}))
                saved=gas_post("saveEASignal",{"signal":sig,"decision":"ENTRY" if ok else "SKIP","reason":reason,
                    "environmentSnapshot":envmap.get(base_symbol,{}),"settingsSnapshot":(cfg.get("pairs") or {}).get(base_symbol,{})})
                if isinstance(saved,dict) and saved.get("signalId"):sig["signalId"]=saved["signalId"]
                if not ok:continue
                pc=(cfg.get("pairs") or {}).get(base_symbol,{})
                order_sig={**sig,"symbol":symbol}
                result=send_order(order_sig,pc)
                gas_post("saveMT5Execution",{"signal":sig,"execution":result})
                logging.info("%s %s %s",symbol,sig["direction"],result)
            except Exception as e:
                logging.exception("%s failed",symbol)
                try:gas_post("saveEAError",{"symbol":symbol,"error":str(e)})
                except Exception:pass
        time.sleep(POLL_SEC)

if __name__=="__main__":
    try:run()
    finally:mt5.shutdown()
