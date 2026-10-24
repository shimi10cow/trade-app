"""Show which MT5 symbol each EA instrument maps to on the logged-in account, its lot rules and a fresh quote (no orders).
Run:  py -m mt5_ea.live.check_symbols   (from the program folder, MT5 open and logged in)"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mt5_ea.live.broker import MT5Broker  # noqa: E402
from mt5_ea.live.registry import SYMBOLS  # noqa: E402

b = MT5Broker(); a = b.account()
print(f"account {a['login']} {a['server']} ({'demo' if a['trade_mode'] == 0 else 'real'}), {a['currency']}, equity {a['equity']:,.0f}")
for s in SYMBOLS:
    try:
        n = b.name(s); sp = b.spec(s); bid, ask = b.quote(s)
        print(f'  OK  {s:7s} -> {n:12s} min lot {sp.volume_min} step {sp.volume_step}  bid {bid} ask {ask}')
    except Exception as e:
        print(f'  NG  {s:7s} {e}')
