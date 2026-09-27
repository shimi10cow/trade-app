"""One-shot DRY-RUN runtime validation. Never sends an order."""
import os, sys, json, tempfile
os.environ["EA_DRY_RUN"]="true"
import MetaTrader5 as mt5
import main
import m15_strategy as strat

ok=True
def check(name,cond,detail=""):
    global ok
    print(("[PASS] " if cond else "[FAIL] ")+name+(f" - {detail}" if detail else ""))
    ok=ok and bool(cond)

try:
    main.connect()
    main.refresh_runtime_once()
    cfg,envs,healthy=main.cached_runtime()
    check("GAS settings cache loaded",isinstance(cfg,dict))
    check("GAS pairs loaded",isinstance(envs,list) and len(envs)>0,f"{len(envs) if isinstance(envs,list) else 0} pairs")
    check("Global entry remains stopped",not bool(cfg.get("globalEntry",False)))
    check("Runtime cache healthy",healthy)
    targets=main.PAIR_OVERRIDE or [main.pair_name(x) for x in envs if main.pair_name(x)]
    tested=0
    with tempfile.TemporaryDirectory() as td:
        old=strat.STATE_PATH
        strat.STATE_PATH=__import__("pathlib").Path(td)/"state.json"
        try:
            for base in sorted(set(targets)):
                sym=main.resolve_symbol(base)
                if not sym: continue
                try:
                    b=main.bars(sym,mt5.TIMEFRAME_M15,3000)
                    check(f"{base} closed M15",len(b)>=2100,f"{len(b)} bars")
                    h1=strat.aggregate_h1([{k:(int(r[k]) if k=="time" else float(r[k])) for k in ("time","open","high","low","close")} for r in b])
                    check(f"{base} causal H1",len(h1)>=505,f"{len(h1)} H1 bars")
                    tick=mt5.symbol_info_tick(sym)
                    spread=max(0.0,float(tick.ask)-float(tick.bid)) if tick and tick.ask and tick.bid else 0.0
                    result=strat.evaluate(base,b,spread)
                    check(f"{base} strategy evaluation",result is None or isinstance(result,dict),"signal" if result else "no signal on latest closed bar")
                    tested+=1
                except Exception as e:
                    print(f"[WARN] {base}: {e}")
        finally:strat.STATE_PATH=old
    check("At least one broker pair fully evaluated",tested>0,f"{tested} pairs")
    check("No live order mode",main.DRY_RUN is True)
finally:
    mt5.shutdown()
print()\nprint("RESULT:","PASS" if ok else "NOT READY")
sys.exit(0 if ok else 1)
