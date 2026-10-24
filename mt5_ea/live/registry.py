"""The adopted EAs (research/INSTRUMENT_PROFILES.md, RESEARCH_LOG §106) as one table the live runner walks through (2026-10-24).

Each entry: key (EA@SYMBOL), symbol, the function that runs it on Frames, lot weight (S / Q on gold: half), filters applied to
NEW entries only (BTC: no Saturday / Sunday entries), and how much M15 history the EA needs.
All functions return dict(trades, open, pending) from the research-identical logic (mt5_ea/live/eas/*).
"""
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from .eas import a as A_, c as C_, ds as DS, j2 as J2, l as L_, q as Q, rsi2 as M, rt as RT, s as S_
from .eas.wave import axis_filter


@dataclass
class EA:
    key: str
    symbol: str
    run: Callable                      # run(F, env) -> dict(trades, open, pending)
    weight: float = 1.0                # lot weight (half lot for gold S / Q)
    window_days: int = 600             # M15 history the live run needs
    warm_days: int = 250               # part of the window only used to build the state
    entry_ok: Callable = field(default=lambda t: True)   # extra check on a new entry's signal time


weekdays = lambda t: pd.Timestamp(t).dayofweek < 5

ADOPTED = [
    EA('R@EURUSD', 'EURUSD', lambda F, env: RT.run(F, 'R2c', env=env), window_days=1100, warm_days=750),   # range score: 3000 H4 bars
    EA('T2@EURUSD', 'EURUSD', lambda F, env: axis_filter(F, RT.run(F, 'T1t', env=env))),
    EA('T@US30', 'US30', lambda F, env: RT.run(F, 'T1t', env=env)),
    EA('L@EURUSD', 'EURUSD', lambda F, env: L_.run(F, env=env)),
    EA('L2@XAUUSD', 'XAUUSD', lambda F, env: L_.run(F, room=1.0, env=env)),
    EA('A@EURUSD', 'EURUSD', lambda F, env: A_.run(F, env=env)),
    EA('C@EURUSD', 'EURUSD', lambda F, env: C_.run(F, env=env)),
    EA('C@USDJPY', 'USDJPY', lambda F, env: C_.run(F, strength=True, env=env)),
    EA('J2@USDJPY', 'USDJPY', lambda F, env: J2.run(F, **J2.ADOPTED['USDJPY'])),
    EA('S@XAUUSD', 'XAUUSD', lambda F, env: S_.run(F, *S_.ADOPTED['XAUUSD']), weight=0.5),
    EA('S@BTCUSD', 'BTCUSD', lambda F, env: S_.run(F, *S_.ADOPTED['BTCUSD']), entry_ok=weekdays),
    EA('Q@XAUUSD', 'XAUUSD', lambda F, env: Q.run(F, *Q.ADOPTED['XAUUSD']), weight=0.5),
    EA('Q@XAGUSD', 'XAGUSD', lambda F, env: Q.run(F, *Q.ADOPTED['XAGUSD'])),
    EA('Q@US30', 'US30', lambda F, env: Q.run(F, *Q.ADOPTED['US30'])),
    EA('M@US30', 'US30', lambda F, env: M.run(F, **M.ADOPTED['US30'])),
    EA('M@US500', 'US500', lambda F, env: M.run(F, **M.ADOPTED['US500'])),
    EA('DS@JP225', 'JP225', lambda F, env: DS.run_adopted(F, 'JP225')),
    EA('DS@US500', 'US500', lambda F, env: DS.run_adopted(F, 'US500')),
    EA('DS@XAUUSD', 'XAUUSD', lambda F, env: DS.run_adopted(F, 'XAUUSD')),
]
BY_KEY = {e.key: e for e in ADOPTED}
SYMBOLS = sorted({e.symbol for e in ADOPTED})
assert len(ADOPTED) == 19
