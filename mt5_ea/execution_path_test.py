"""End-to-end DRY RUN execution-path self-test.

Uses live MT5 market/spec data but NEVER sends an order and NEVER mutates strategy state.
It exercises: symbol resolution -> synthetic strategy-approved signal -> allow gates ->
order sizing/risk -> MT5 order_check -> GAS outbox enqueue.
"""
import os, sys, time, sqlite3
os.environ["EA_DRY_RUN"]="true"
import MetaTrader5 as mt5
import main

PAIR=os.getenv("EA_SELFTEST_PAIR","EURUSD")
TEST_MAGIC_PREFIX="SELFTEST-"

def fail(msg):
    print("[FAIL]",msg)
    raise SystemExit(1)

try:
    main.connect()
    main.init_outbox()
    cache_loaded=main.load_runtime_disk_cache()
    cfg,envs,runtime_ok=main.cached_runtime()
    symbol=main.resolve_symbol(PAIR)
    if not symbol: fail(f"{PAIR}: broker symbol not found")
    tick=mt5.symbol_info_tick(symbol)
    info=mt5.symbol_info(symbol)
    if not tick or not info or not tick.ask or not tick.bid: fail(f"{PAIR}: live tick/spec unavailable")

    # This is deliberately synthetic: it tests the post-strategy plumbing without touching m15_state.json.
    entry=float(tick.ask)
    distance=max(float(info.point)*100, abs(entry)*0.001)
    sl=entry-distance
    sig={"symbol":PAIR,"brokerSymbol":symbol,"direction":"BUY","strategyAllowed":True,
         "strategyReason":"OK","pattern":"SELFTEST","rule":"SELFTEST","entry":entry,"sl":sl,
         "initialRisk":distance,"spreadPrice":max(0.0,float(tick.ask)-float(tick.bid))}

    # Verify policy gates independently. Existing user settings may intentionally be STOP.
    gate_ok,gate_reason=main.allowed(sig,cfg,{})
    print(f"[PASS] policy gate evaluated: allowed={gate_ok} reason={gate_reason}")
    print(f"[PASS] runtime cache evaluated: loaded={cache_loaded} healthy={runtime_ok}")

    # Use a dedicated safe fixed-lot config so broker order_check can be exercised even while GAS is STOP.
    pc={"mode":"auto","direction":"Both","m15":True,"riskType":"fixedLot",
        "riskValue":max(float(info.volume_min),0.01),"riskCapEnabled":False,"riskCap":100.0}
    safe_cfg={"totalRiskCapEnabled":False}
    result=main.send_order({**sig,"symbol":symbol},pc,safe_cfg)
    if not result.get("dry_run"): fail("DRY RUN guard failed")
    print("[PASS] MT5 order_check passed; order_send was NOT called")

    sid=f"{TEST_MAGIC_PREFIX}{PAIR}-{int(time.time())}"
    main.enqueue_gas("saveEASignal",{"data":{"SignalID":sid,"SignalTime":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "Pair":PAIR,"Direction":"BUY","Rule":"SELFTEST","Pullback":"SELFTEST","Executed":"DRY_RUN",
        "SkipReason":"SELFTEST_ONLY","EntryPrice":entry,"InitialSL":sl,
        "InitialRiskPips":distance/main.m15_pip_size(PAIR),
        "SpreadPips":sig["spreadPrice"]/main.m15_pip_size(PAIR)}})
    with sqlite3.connect(main.OUTBOX_DB) as db:
        row=db.execute("SELECT id FROM outbox WHERE payload LIKE ? ORDER BY id DESC LIMIT 1",(f'%{sid}%',)).fetchone()
    if not row: fail("GAS outbox enqueue failed")
    print("[PASS] GAS persistence path queued locally (network wait not required)")
    print("RESULT: END-TO-END DRY RUN PASS")
finally:
    mt5.shutdown()
