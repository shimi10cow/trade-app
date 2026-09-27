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
    """Resolve only the XM KIWAMI symbol that corresponds to the logical pair."""
    b="".join(x for x in str(base).upper() if x.isalnum())
    target="GOLD#" if b=="XAUUSD" else (b+"#" if len(b)==6 and b.isalpha() else None)
    if not target:
        return None
    return target if mt5.symbol_info(target) else None

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
        sym=resolve(p); info=mt5.symbol_info(sym) if sym else None
        if sym and info and not info.visible: mt5.symbol_select(sym,True); info=mt5.symbol_info(sym)
        # Pre-live readiness validates broker symbol/spec availability only. A stale/zero
        # tick while the market is closed is not a deployment failure; send_order performs
        # the fresh-price check again immediately before any real order.
        ok=bool(sym and info and int(info.trade_mode)!=mt5.SYMBOL_TRADE_MODE_DISABLED and float(info.volume_min)>0 and float(info.volume_step)>0)
        print(("[PASS] " if ok else "[FAIL] ")+f"{p} broker spec ({sym or 'NOT FOUND'})"); bad|=not ok
    print(("[PASS] " if algo else "[FINAL ACTION] ")+"MT5 Algo Trading "+("ON" if algo else "OFF"))
    if bad:
        print("RESULT: NOT READY"); sys.exit(1)
    print("RESULT: READY; ONLY ALGO TRADING SWITCH REMAINS" if not algo else "RESULT: READY")
finally:
    mt5.shutdown()
