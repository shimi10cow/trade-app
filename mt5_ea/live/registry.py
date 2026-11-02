"""The adopted EAs (research/INSTRUMENT_PROFILES.md, RESEARCH_LOG §106) as one table the live runner walks through (2026-10-24).
2026-11-02 (docs/EA_PLAN_20261102.md): H4 opening gate on C@USDJPY, T@US30, Q@XAGUSD, Q@US30, DS@JP225; H4 MA75 slope gate on
R@EURUSD; new trend EA P@ on XAUUSD / EURUSD / USDJPY.
2026-11 (RESEARCH_LOG §158): P's 'not after a long H1 run' gate on C@EURUSD and A@EURUSD, 'no level bounce' gate on T@US30.

Each entry: key (EA@SYMBOL), symbol, the function that runs it on Frames, lot weight (S / Q on gold: half), filters applied to
NEW entries only (BTC: no Saturday / Sunday entries), and how much M15 history the EA needs.
All functions return dict(trades, open, pending) from the research-identical logic (mt5_ea/live/eas/*).
"""
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from .eas import a as A_, c as C_, ds as DS, j2 as J2, l as L_, nt as NT, q as Q, rsi2 as M, rt as RT, s as S_
from .eas.h4gate import gate
from .eas.pgate import gate as pgate
from .eas.wave import axis_filter


@dataclass
class EA:
    key: str
    symbol: str
    run: Callable                      # run(F, env) -> dict(trades, open, pending)
    weight: float = 1.0                # default lot weight (half lot for gold S / Q)
    weight_choices: tuple = (1.0,)     # weights the app may switch to (gold S / Q: half or full)
    window_days: int = 600             # M15 history the live run needs
    warm_days: int = 250               # part of the window only used to build the state
    entry_ok: Callable = field(default=lambda t: True)   # extra check on a new entry's signal time


weekdays = lambda t: pd.Timestamp(t).dayofweek < 5

ADOPTED = [
    EA('R@EURUSD', 'EURUSD', gate(lambda F, env: RT.run(F, 'R2c', env=env), 'slope'), window_days=1100, warm_days=750),   # range score: 3000 H4 bars
    EA('T2@EURUSD', 'EURUSD', lambda F, env: axis_filter(F, RT.run(F, 'T1t', env=env))),
    EA('T@US30', 'US30', pgate(gate(lambda F, env: RT.run(F, 'T1t', env=env), 'open'), 'band')),
    EA('L@EURUSD', 'EURUSD', lambda F, env: L_.run(F, env=env)),
    EA('L2@XAUUSD', 'XAUUSD', lambda F, env: L_.run(F, room=1.0, env=env)),
    EA('A@EURUSD', 'EURUSD', pgate(lambda F, env: A_.run(F, env=env), 'ext')),
    EA('C@EURUSD', 'EURUSD', pgate(lambda F, env: C_.run(F, env=env), 'ext')),
    EA('C@USDJPY', 'USDJPY', gate(lambda F, env: C_.run(F, strength=True, notri=False, env=env), 'open')),
    EA('J2@USDJPY', 'USDJPY', lambda F, env: J2.run(F, **J2.ADOPTED['USDJPY'])),
    EA('S@XAUUSD', 'XAUUSD', lambda F, env: S_.run(F, *S_.ADOPTED['XAUUSD']), weight=0.5, weight_choices=(0.5, 1.0)),
    EA('S@BTCUSD', 'BTCUSD', lambda F, env: S_.run(F, *S_.ADOPTED['BTCUSD']), entry_ok=weekdays),
    EA('Q@XAUUSD', 'XAUUSD', lambda F, env: Q.run(F, *Q.ADOPTED['XAUUSD']), weight=0.5, weight_choices=(0.5, 1.0)),
    EA('Q@XAGUSD', 'XAGUSD', gate(lambda F, env: Q.run(F, *Q.ADOPTED['XAGUSD']), 'open')),
    EA('Q@US30', 'US30', gate(lambda F, env: Q.run(F, *Q.ADOPTED['US30']), 'open')),
    EA('M@US30', 'US30', lambda F, env: M.run(F, **M.ADOPTED['US30'])),
    EA('M@US500', 'US500', lambda F, env: M.run(F, **M.ADOPTED['US500'])),
    EA('DS@JP225', 'JP225', gate(lambda F, env: DS.run_adopted(F, 'JP225'), 'open')),
    EA('DS@US500', 'US500', lambda F, env: DS.run_adopted(F, 'US500')),
    EA('DS@XAUUSD', 'XAUUSD', lambda F, env: DS.run_adopted(F, 'XAUUSD')),
    # P: new trend EA (2026-11-02): appended at the end so the existing magic numbers stay the same
    EA('P@XAUUSD', 'XAUUSD', lambda F, env: NT.run(F, 'XAUUSD'), window_days=800, warm_days=400),
    EA('P@EURUSD', 'EURUSD', lambda F, env: NT.run(F, 'EURUSD'), window_days=800, warm_days=400),
    EA('P@USDJPY', 'USDJPY', lambda F, env: NT.run(F, 'USDJPY'), window_days=800, warm_days=400),
]
BY_KEY = {e.key: e for e in ADOPTED}
SYMBOLS = sorted({e.symbol for e in ADOPTED})
assert len(ADOPTED) == 22
