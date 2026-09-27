"""One-shot XM MT5 + GAS connection check. Never places orders."""
import os, sys, requests
import MetaTrader5 as mt5

DEFAULT_GAS="https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
GAS=os.getenv("EA_GAS_URL",DEFAULT_GAS)
REQUESTED=[x.strip() for x in os.getenv("EA_PAIRS","").split(",") if x.strip()]

def gas(action):
    r=requests.get(GAS,params={"action":action},timeout=15)
    r.raise_for_status()
    try:
        x=r.json()
    except Exception:
        preview=(r.text or "")[:300].replace("\r"," ").replace("\n"," ")
        raise RuntimeError(f"GAS returned non-JSON: status={r.status_code} final_url={r.url} body={preview!r}")
    if x.get("success") is False: raise RuntimeError(x.get("error",x))
    return x.get("data",x)

def norm(s):
    return "".join(c for c in str(s).upper() if c.isalnum())

def resolve_symbol(base):
    if mt5.symbol_info(base): return base
    b=norm(base); aliases=[b]
    if b=="XAUUSD": aliases+=["GOLD"]
    candidates=[]
    for x in mt5.symbols_get() or []:
        n=norm(x.name)
        if any(a in n for a in aliases):
            candidates.append(x.name)
    if not candidates: return None
    candidates.sort(key=lambda n:(0 if norm(n).startswith(b) else 1,len(n)))
    return candidates[0]

def tracker_pairs():
    rows=gas("getPairs") or []
    out=[]
    for r in rows:
        if not isinstance(r,dict): continue
        p=r.get("PairName（元）") or r.get("PairName") or r.get("Pair") or r.get("通貨ペア") or r.get("pair")
        if p: out.append(str(p).strip())
    if not out and rows:
        print(f"[DEBUG] getPairs first row keys={list(rows[0].keys()) if isinstance(rows[0],dict) else type(rows[0]).__name__}")
    return sorted(set(out))

def target_pairs():
    # EA_PAIRS is only an optional temporary override.
    # Normal operation follows Trade Tracker's Pairs list, so Python has no 5-pair ceiling.
    return REQUESTED or tracker_pairs()

ok=True
try:
    if not mt5.initialize(): raise RuntimeError(mt5.last_error())
    a=mt5.account_info()
    if not a: raise RuntimeError("account_info unavailable")
    print(f"[PASS] MT5 login={a.login} server={a.server} balance={a.balance}")

    try:
        pairs=target_pairs()
    except Exception as e:
        print(f"[FAIL] GAS getPairs before MT5 scan: {e}")
        pairs=[]
        ok=False
    print(f"[INFO] Trade Tracker target pairs={len(pairs)}")
    usable=0
    for base in pairs:
        s=resolve_symbol(base)
        if not s:
            print(f"[WARN] {base}: broker symbol not found")
            continue
        if not mt5.symbol_select(s,True):
            print(f"[WARN] {base}: symbol_select failed ({s})")
            continue
        tick=mt5.symbol_info_tick(s)
        rates=mt5.copy_rates_from_pos(s,mt5.TIMEFRAME_M15,0,3)
        if rates is None or len(rates)<3:
            print(f"[WARN] {base} -> {s}: M15 unavailable")
            continue
        bid=getattr(tick,"bid",0) if tick else 0
        ask=getattr(tick,"ask",0) if tick else 0
        print(f"[PASS] {base} -> {s}: bid={bid} ask={ask} closed_M15={int(rates[-2]['time'])}")
        usable+=1
    if usable==0:
        print("[FAIL] no usable MT5 symbols"); ok=False

    # Existing deployments may not yet expose EA settings. Pairs connectivity is the hard requirement here.
    try:
        d=gas("getEASettings")
        print(f"[PASS] GAS getEASettings: type={type(d).__name__} size={len(d) if hasattr(d,'__len__') else '-'}")
    except Exception as e:
        print(f"[WARN] GAS getEASettings not exposed yet: {e}")
        print("[INFO] Deploy the latest Code.gs web-app version before runtime settings sync.")
    try:
        d=gas("getPairs")
        print(f"[PASS] GAS getPairs: type={type(d).__name__} size={len(d) if hasattr(d,'__len__') else '-'}")
    except Exception as e:
        print(f"[FAIL] GAS getPairs: {e}");ok=False
finally:
    mt5.shutdown()

print()
print("RESULT:", "READY FOR DRY RUN" if ok else "FIX FAILED ITEMS FIRST")
sys.exit(0 if ok else 1)
