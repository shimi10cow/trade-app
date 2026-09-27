"""Final no-order LIVE readiness test. It never imports main.py and never calls order_send."""
import os, sys, time
import MetaTrader5 as mt5

PAIRS=["EURUSD","USDJPY","EURJPY","AUDJPY","XAUUSD"]
login=os.getenv("EA_LIVE_LOGIN","").strip()
server=os.getenv("EA_LIVE_SERVER","").strip()
if not login or not server:
    print("[FAIL] LIVE account lock missing"); sys.exit(1)
if not mt5.initialize():
    print("[FAIL] MT5 initialize",mt5.last_error()); sys.exit(1)

def resolve(base):
    if mt5.symbol_info(base): return base
    b="".join(x for x in base.upper() if x.isalnum())
    aliases=[b]+(["GOLD"] if b=="XAUUSD" else [])
    hits=[x.name for x in (mt5.symbols_get() or []) if any(a in "".join(c for c in x.name.upper() if c.isalnum()) for a in aliases)]
    hits.sort(key=lambda n:(0 if "".join(c for c in n.upper() if c.isalnum()).startswith(b) else 1,len(n)))
    return hits[0] if hits else None

bad=False
try:
    a=mt5.account_info(); t=mt5.terminal_info()
    checks=[
      ("account lock",bool(a) and str(a.login)==login and str(a.server)==server),
      ("REAL account",bool(a) and a.trade_mode==mt5.ACCOUNT_TRADE_MODE_REAL),
      ("positive equity",bool(a) and float(a.equity)>0),
      ("account trade allowed",bool(a) and bool(a.trade_allowed)),
      ("terminal connected",bool(t) and bool(t.connected)),
      ("LIVE remains disarmed",os.getenv("EA_LIVE_ARMED","false").lower()!="true"),
    ]
    # Algo Trading is intentionally the one final manual switch and is reported separately.
    algo=bool(t) and bool(t.trade_allowed)
    for name,ok in checks:
        print(("[PASS] " if ok else "[FAIL] ")+name); bad|=not ok
    for p in PAIRS:
        sym=resolve(p); info=mt5.symbol_info(sym) if sym else None; tick=mt5.symbol_info_tick(sym) if sym else None
        ok=bool(sym and info and tick and tick.bid and tick.ask and int(info.trade_mode)!=mt5.SYMBOL_TRADE_MODE_DISABLED and time.time()-float(tick.time)<=300)
        print(("[PASS] " if ok else "[FAIL] ")+f"{p} market/spec ({sym or 'NOT FOUND'})"); bad|=not ok
    print(("[PASS] " if algo else "[FINAL ACTION] ")+"MT5 Algo Trading "+("ON" if algo else "OFF"))
    if bad:
        print("RESULT: NOT READY"); sys.exit(1)
    print("RESULT: READY; ONLY ALGO TRADING SWITCH REMAINS" if not algo else "RESULT: READY")
finally:
    mt5.shutdown()
