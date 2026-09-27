"""Hybrid EA runner. Start with DRY_RUN=true. Windows + MT5 terminal + Python 3.11."""
import os,time,json,logging
from datetime import datetime,timezone
import requests
import MetaTrader5 as mt5

GAS_URL=os.getenv("EA_GAS_URL","")
DRY_RUN=os.getenv("EA_DRY_RUN","true").lower()=="true"
POLL_SEC=int(os.getenv("EA_POLL_SEC","2"))
MAGIC=int(os.getenv("EA_MAGIC","560001"))
PAIRS=[x.strip() for x in os.getenv("EA_PAIRS","EURUSD,USDJPY,EURJPY,AUDJPY,XAUUSD").split(",") if x.strip()]
logging.basicConfig(level=logging.INFO,format="%(asctime)s %(levelname)s %(message)s")
last_bar={}

def gas_get(action,**params):
    if not GAS_URL:return {}
    r=requests.get(GAS_URL,params={"action":action,**params},timeout=10);r.raise_for_status()
    x=r.json();return x.get("data",x)

def gas_post(action,data):
    if not GAS_URL:return
    r=requests.post(GAS_URL,json={"action":action,**data},timeout=10);r.raise_for_status()

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
    if pc.get("mode","stop")=="stop":return False,"PAIR_STOP"
    if not pc.get("m15",True):return False,"M15_OFF"
    d=str(pc.get("direction","Both")).upper()
    if d not in ("BOTH","両方",sig["direction"].upper()):return False,"DIRECTION_BLOCK"
    return True,"OK"

def lot_for(symbol,entry,sl,pc):
    # Safe V1: fixed lot by default. Risk-% calculation is added after broker symbol specs are verified.
    lot=float(pc.get("lot",0.01) or 0.01)
    info=mt5.symbol_info(symbol)
    if not info:raise RuntimeError(f"{symbol}: symbol_info unavailable")
    step=info.volume_step or 0.01
    lot=max(info.volume_min,min(info.volume_max,round(lot/step)*step))
    return lot

def send_order(sig,pc):
    symbol=sig["symbol"];tick=mt5.symbol_info_tick(symbol)
    if not tick:raise RuntimeError(f"{symbol}: no tick")
    buy=sig["direction"].upper()=="BUY";price=tick.ask if buy else tick.bid
    lot=lot_for(symbol,price,float(sig["sl"]),pc)
    req={"action":mt5.TRADE_ACTION_DEAL,"symbol":symbol,"volume":lot,
         "type":mt5.ORDER_TYPE_BUY if buy else mt5.ORDER_TYPE_SELL,
         "price":price,"sl":float(sig["sl"]),"deviation":20,"magic":MAGIC,
         "comment":"HybridEA-M15","type_time":mt5.ORDER_TIME_GTC,"type_filling":mt5.ORDER_FILLING_IOC}
    if sig.get("tp"):req["tp"]=float(sig["tp"])
    if DRY_RUN:return {"dry_run":True,"request":req}
    res=mt5.order_send(req)
    if res is None or res.retcode!=mt5.TRADE_RETCODE_DONE:raise RuntimeError(f"order_send failed: {res}")
    return {"dry_run":False,"order":res.order,"deal":res.deal,"price":res.price,"volume":res.volume}

def run():
    connect()
    while True:
        cfg=pair_settings();envs=environment()
        envmap={str(x.get("Pair") or x.get("PairName") or x.get("通貨ペア") or ""):x for x in envs if isinstance(x,dict)}
        for symbol in PAIRS:
            try:
                b=bars(symbol,mt5.TIMEFRAME_M15)
                ts=int(b[-1]["time"])
                if last_bar.get(symbol)==ts:continue
                last_bar[symbol]=ts
                raw=evaluate_m15(symbol,b,cfg,envmap.get(symbol,{}))
                if not raw:continue
                sig={"symbol":symbol,"time":datetime.fromtimestamp(ts,timezone.utc).isoformat(),**raw}
                ok,reason=allowed(sig,cfg,envmap.get(symbol,{}))
                gas_post("saveEASignal",{"signal":sig,"decision":"ENTRY" if ok else "SKIP","reason":reason,
                    "environmentSnapshot":envmap.get(symbol,{}),"settingsSnapshot":(cfg.get("pairs") or {}).get(symbol,{})})
                if not ok:continue
                pc=(cfg.get("pairs") or {}).get(symbol,{})
                result=send_order(sig,pc)
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
