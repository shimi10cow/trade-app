"""One-shot LIVE safety-gate verification. NEVER sends an order."""
import os, sys
import MetaTrader5 as mt5

login=os.getenv("EA_LIVE_LOGIN","").strip()
server=os.getenv("EA_LIVE_SERVER","").strip()
if not login or not server:
    print("[FAIL] EA_LIVE_LOGIN / EA_LIVE_SERVER not configured"); sys.exit(1)
if not mt5.initialize():
    print("[FAIL] MT5 initialize",mt5.last_error()); sys.exit(1)
try:
    a=mt5.account_info(); t=mt5.terminal_info()
    checks=[
        ("account available",bool(a)),
        ("terminal available",bool(t)),
        ("account lock",bool(a) and str(a.login)==login and str(a.server)==server),
        ("positive equity",bool(a) and float(a.equity)>0),
        ("account trade allowed",bool(a) and bool(a.trade_allowed)),
        ("terminal trade allowed",bool(t) and bool(t.trade_allowed)),
    ]
    bad=False
    for name,ok in checks:
        print(("[PASS] " if ok else "[FAIL] ")+name); bad|=not ok
    # Prove the real-order arm remains off. This script never imports/calls order_send.
    armed=os.getenv("EA_LIVE_ARMED","false").lower()=="true"
    safe=not armed
    print(("[PASS] " if safe else "[FAIL] ")+"LIVE remains disarmed")
    bad|=not safe
    print("RESULT:","LIVE SAFETY READY (DISARMED)" if not bad else "NOT READY")
    sys.exit(1 if bad else 0)
finally:
    mt5.shutdown()
