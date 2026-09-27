"""Preflight for Hybrid EA. Does not place orders."""
import ast, pathlib, os, sys
ROOT=pathlib.Path(__file__).parent
files=["main.py","m15_strategy.py","connection_test.py"]
bad=[]
for name in files:
    p=ROOT/name
    try:
        ast.parse(p.read_text(encoding="utf-8"),filename=name)
        print(f"[PASS] syntax {name}")
    except Exception as e:
        bad.append(f"{name}: {e}"); print(f"[FAIL] syntax {name}: {e}")
main=(ROOT/"main.py").read_text(encoding="utf-8")
strategy=(ROOT/"m15_strategy.py").read_text(encoding="utf-8")
checks={
 "DRY_RUN defaults true":'EA_DRY_RUN","true"' in main,
 "M15 history >=3000":"count=3000" in main,
 "GAS settings cache 300s":'>=300' in main,
 "GAS environment refresh configured":"ENV_FETCH_SEC=60" in main,
 "Stoch smoothing 5 then 3":"k=nullable_sma(raw,5)" in strategy and "nullable_sma(k,3)" in strategy,
 "Retracement Gate":"RETRACEMENT_P1_LT15" in strategy and "RETRACEMENT_NEGATIVE" in strategy,
 "H1 Extreme Switch":"H1_EXTREME_SWITCH" in strategy,
 "SMA480 24h":"s480[i-24]" in strategy,
 "Spread/risk 10%":"spread_price/risk>.10" in strategy,
 "240h activates trailing, not forced exit":"age_hours>=240.0" in strategy and "TIME_EXIT" not in strategy and "forces an exit" in strategy.lower(),
 "P3 causal ledger implemented":"trade_id" in strategy and "update_trade_ledger" in strategy and "trade_r" in strategy,
 "Spread included in R":"spread_r" in strategy,
 "Async GAS runtime":"runtime_refresher" in main and "outbox_worker" in main and "RUNTIME_CACHE_STALE" in main,
 "Persistent GAS outbox":"sqlite3" in main and "next_attempt" in main and "attempts" in main,
 "Environment freshness + direction":"ENV_TIME_MISSING" in main and "ENV_DIRECTION_BLOCK" in main and "envRefreshMin" in main,
 "Total simultaneous risk cap":"TOTAL_RISK_CAP" in main and "open_ea_risk" in main,
 "Restart bootstrap":"bootstrap_missing_state" in main and "bootstrap_m15" in main,
 "Bootstrap precomputed replay":"_bootstrap_cache" in strategy and "_cache=cache" in strategy and "_state=state,_save=False" in strategy,
 "Incremental market polling":"latest_closed_bar_time" in main and "evaluate_missing_m15" in main and "bars_since" in main,
 "Single MT5 position snapshot":"all_positions=[p for p in (mt5.positions_get() or [])" in main,
 "Windows-safe state writes":'STATE_PATH.open("w",encoding="utf-8")' in strategy and "os.fsync" in strategy and "os.replace(name,STATE_PATH)" not in strategy,
 "Virtual trade tracking":"virtual_trades" in strategy and "collect_virtual_updates" in strategy,
 "MT5 position recovery":"recover_m15_execution" in main and "RECOVERED:" in strategy,
 "LIVE explicit arm gate":'LIVE_ARMED=os.getenv("EA_LIVE_ARMED","false")' in main and "LIVE_NOT_ARMED" in main,
 "LIVE account/server lock":"LIVE_ACCOUNT_LOCK_MISMATCH" in main and "EA_LIVE_LOGIN" in main and "EA_LIVE_SERVER" in main,
 "LIVE account/terminal permissions":"ACCOUNT_TRADE_NOT_ALLOWED" in main and "TERMINAL_TRADE_NOT_ALLOWED" in main and "TERMINAL_NOT_CONNECTED" in main,
 "LIVE gate also protects SL modifications":"def modify_position_sl(position,new_sl):\n    if DRY_RUN:return True\n    live_safety_check()" in main,
 "LIVE positive equity gate":"LIVE_EQUITY_NOT_POSITIVE" in main,
 "LIVE requires real account":"LIVE_ACCOUNT_NOT_REAL" in main and "EA_LIVE_REQUIRE_REAL" in main,
 "LIVE symbol trading gate":"SYMBOL_TRADE_MODE_DISABLED" in main and "trading disabled" in main,
 "LIVE app risk settings fail closed":"LIVE_RISK_CONFIG_INVALID" in main and "validate_live_pair_config" in main,
 "Offline catch-up never executes stale signal":"OFFLINE_CATCHUP" in main and "MAX_SIGNAL_AGE_SEC" in main,
}
for k,v in checks.items():
    print(("[PASS] " if v else "[FAIL] ")+k)
    if not v:bad.append(k)
if os.getenv("EA_DRY_RUN","true").lower()!="true":
    bad.append("EA_DRY_RUN must remain true for this preflight")
    print("[FAIL] EA_DRY_RUN is not true")
else: print("[PASS] EA_DRY_RUN=true")
print()
print("RESULT:", "PASS" if not bad else "NOT READY")
if bad:
    print("FAILED:")
    for x in bad: print(" - "+x)
    sys.exit(1)
