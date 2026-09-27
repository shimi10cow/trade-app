"""One-shot connection check. Does NOT place orders."""
import json, os, sys
import requests
import MetaTrader5 as mt5

DEFAULT_GAS="https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
GAS=os.getenv("EA_GAS_URL",DEFAULT_GAS)
PAIRS=[x.strip() for x in os.getenv("EA_PAIRS","EURUSD,USDJPY,EURJPY,AUDJPY,XAUUSD").split(",") if x.strip()]

def gas(action):
    r=requests.get(GAS,params={"action":action},timeout=15);r.raise_for_status()
    x=r.json()
    if x.get("success") is False: raise RuntimeError(x.get("error",x))
    return x.get("data",x)

ok=True
try:
    if not mt5.initialize(): raise RuntimeError(mt5.last_error())
    a=mt5.account_info()
    if not a: raise RuntimeError("account_info unavailable")
    print(f"[PASS] MT5 login={a.login} server={a.server} balance={a.balance}")
    for s in PAIRS:
        if not mt5.symbol_select(s,True):
            print(f"[FAIL] {s}: symbol_select");ok=False;continue
        tick=mt5.symbol_info_tick(s)
        rates=mt5.copy_rates_from_pos(s,mt5.TIMEFRAME_M15,0,3)
        if tick is None or rates is None or len(rates)<3:
            print(f"[FAIL] {s}: tick/M15 unavailable");ok=False
        else:
            print(f"[PASS] {s}: bid={tick.bid} ask={tick.ask} closed_M15={int(rates[-2]['time'])}")
    for action in ("getEASettings","getPairs"):
        try:
            d=gas(action)
            n=len(d) if hasattr(d,"__len__") else "-"
            print(f"[PASS] GAS {action}: type={type(d).__name__} size={n}")
        except Exception as e:
            print(f"[FAIL] GAS {action}: {e}");ok=False
finally:
    mt5.shutdown()
print("\nRESULT:", "READY FOR DRY RUN" if ok else "FIX FAILED ITEMS FIRST")
sys.exit(0 if ok else 1)
