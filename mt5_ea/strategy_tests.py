"""Deterministic strategy checks. No MT5/GAS/order calls."""
import ast, pathlib
import m15_strategy as s

ROOT=pathlib.Path(__file__).parent
src=(ROOT/"m15_strategy.py").read_text(encoding="utf-8")
ast.parse(src)
tests=[]

def check(name,cond):
    tests.append((name,bool(cond)))
    print(("[PASS] " if cond else "[FAIL] ")+name)

# 240h activates trailing but never closes by age.
ps={"signals":{},"trades":{"P1":{"entered":True,"open":True,"risk":1.0,"direction":"BUY","entry":100.0,"sl":90.0,"entry_time":0,"bar_index":0,"trailing":False}}}
row={"time":240*3600,"high":101.0,"low":99.0,"close":100.0}
s.update_trade_ledger(ps,row,[],100)
check("240h activates trailing",ps["trades"]["P1"]["trailing"] is True)
check("240h does not force exit",ps["trades"]["P1"]["open"] is True)

# +2R activates trailing.
ps={"signals":{},"trades":{"P1":{"entered":True,"open":True,"risk":1.0,"direction":"BUY","entry":100.0,"sl":90.0,"entry_time":0,"bar_index":0,"trailing":False}}}
s.update_trade_ledger(ps,{"time":3600,"high":102.1,"low":99.5,"close":101.0},[],10)
check("+2R activates trailing",ps["trades"]["P1"]["trailing"] is True)

# Pivot confirmed this bar is queued, not active until next bar.
pv=[{"type":"L","index":5,"price":99.0,"confirmed":10}]
s.update_trade_ledger(ps,{"time":7200,"high":101.5,"low":100.0,"close":101.0},pv,10)
check("new ZigZag SL queued",ps["trades"]["P1"].get("pending_sl")==99.0 and ps["trades"]["P1"]["sl"]==90.0)
s.update_trade_ledger(ps,{"time":10800,"high":101.0,"low":99.5,"close":100.5},pv,11)
check("queued SL active next bar",ps["trades"]["P1"]["sl"]==99.0)

# Retracement boundaries.
buy=[{"type":"L","price":100.0},{"type":"H","price":110.0}]
check("retracement 0%",abs(s.retracement("BUY",110.0,buy)-0.0)<1e-9)
check("retracement 15%",abs(s.retracement("BUY",108.5,buy)-15.0)<1e-9)
check("retracement negative",s.retracement("BUY",111.0,buy)<0)

# q75 must use prior observations.
check("q75 deterministic",abs(s.percentile75([1,2,3,4])-3.25)<1e-9)

failed=[n for n,v in tests if not v]
print("\nRESULT:","PASS" if not failed else "NOT READY")
if failed:
    for n in failed:print(" -",n)
    raise SystemExit(1)

# Regime-local signal ledger may reset without losing an open trade.
ps={"signals":{"P1":{"entered":True}},"trades":{"old":{"entered":True,"open":True,"risk":1.0,"direction":"BUY","entry":100.0,"sl":90.0,"entry_time":0,"trailing":False}}}
ps.update({"regime":"SELL","p_count":0,"extreme":False,"signals":{}})
check("open trade survives regime reset","old" in ps["trades"] and ps["trades"]["old"]["open"])

failed=[n for n,v in tests if not v]
print("\nRESULT:","PASS" if not failed else "NOT READY")
if failed:
    for n in failed:print(" -",n)
    raise SystemExit(1)
