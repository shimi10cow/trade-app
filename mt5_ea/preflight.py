"""Preflight for Hybrid EA. Does not place orders."""
import ast, pathlib, os, sys
ROOT=pathlib.Path(__file__).parent
files=["main.py","m15_strategy.py","h1_strategy.py","telegram_notify.py","connection_test.py"]
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
h1=(ROOT/"h1_strategy.py").read_text(encoding="utf-8")
checks={
 "H1 strategy module present":(ROOT/"h1_strategy.py").exists(),
 "Telegram notification module present":(ROOT/"telegram_notify.py").exists(),
 "Telegram wired to runtime":"import telegram_notify as telegram" in main and "notifySignal" in main and "notifyEntry" in main and "notifyError" in main,
 "Telegram global Exit toggle available":"notifyExit" in main,
 "H1 independent of M15 signal":"if results:process_signal" in main and "if pc.get(\"h1\",False)" in main,
 "Shared actual position cap":'if len(current)>=2:raise RuntimeError("MAX_POSITIONS")' in main,
 "H1 app toggle wired":'pc.get("h1",False)' in main and '"H1_OFF"' in main,
 "H1 live execution wired":"register_h1_execution" in main and '"timeframe":"H1"' in main,
 "H1 closed-bar only":'!=45:return None' in h1,
 "H1 Stoch 14-5-3":"nullable_sma(raw,5)" in h1 and "nullable_sma(k,3)" in h1,
 "H1 W4+ rejected":'W4_PLUS' in h1,
 "H1 shares causal exit ledger":"recover_m15_execution" in main and '"Source":"EA-H1"' in main,
 "DRY_RUN defaults true":'EA_DRY_RUN","true"' in main,
 "M15 history >=3000":"count=3000" in main,
 "GAS settings refresh configurable":"settingsRefreshMin" in main and "settings_interval=max(30.0" in main,
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
 "App global stop immediate contract":'gas_get("getAppSettings")' in main and "CONTROL_FETCH_SEC" in main and 'GLOBAL_STOP' in main,
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
 "LIVE requires fresh tick at execution":"stale tick" in main and 'not getattr(tick,"time",0)' in main,
 "Broker minimum stop distance":"BROKER_STOPS_LEVEL" in main and "trade_stops_level" in main,
 "Broker filling mode negotiation":"order_check rejected all filling modes" in main and "ORDER_FILLING_IOC" in main,
 "Offline catch-up never executes stale signal":"OFFLINE_CATCHUP" in main and "MAX_SIGNAL_AGE_SEC" in main,
 "XM KIWAMI exact symbol mapping":'target="GOLD#" if b=="XAUUSD"' in main and 'b+"#"' in main and "symbols_get()" not in main,
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


def check_app_kill_switch_contract():
    root=Path(__file__).resolve().parents[1]
    ea=(root/"ea.js").read_text(encoding="utf-8")
    main=(root/"mt5_ea"/"main.py").read_text(encoding="utf-8")
    assert "window.eaGlobal=async function" in ea
    assert "saveAppSettings" in ea and "globalEntry:v?'ON':'OFF'" in ea
    assert 'gas_get("getAppSettings")' in main
    assert "CONTROL_FETCH_SEC" in main
    assert 'if not cfg.get("globalEntry",False):return False,"GLOBAL_STOP"' in main
