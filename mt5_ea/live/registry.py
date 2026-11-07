"""The adopted EAs (research/INSTRUMENT_PROFILES.md, RESEARCH_LOG §106) as one table the live runner walks through (2026-10-24).
2026-11-02 (docs/EA_PLAN_20261102.md): H4 opening gate on C@USDJPY, T@US30, Q@XAGUSD, Q@US30, DS@JP225; H4 MA75 slope gate on
R@EURUSD; new trend EA P@ on XAUUSD / EURUSD / USDJPY.
2026-11 (RESEARCH_LOG §158): P's 'not after a long H1 run' gate on C@EURUSD and A@EURUSD, 'no level bounce' gate on T@US30.
2026-11-04 (RESEARCH_LOG §176 / §174): P@US500 / P@US100; J2@USDJPY weekly trend instead of the hour window.
2026-11-03 (RESEARCH_LOG §164-§166): new return move RM@ on EURUSD / XAUUSD (A@EURUSD stays off in the app).
2026-11-07 (docs/OPEN_ITEMS.md): DL@EURUSD / DL@USDJPY (daily-line zone), HL@EURUSD (H4 trendline), Q@BTCUSD; Q one setting + run filter
(Q@XAGUSD without the H4 gate, Q@US30 off in the app); lower-high exit on J2@USDJPY / P@USDJPY for new entries.

Each entry: key (EA@SYMBOL), symbol, the function that runs it on Frames, lot weight (full by default; half selectable in the app), filters applied to
NEW entries only (BTC: no Saturday / Sunday entries), and how much M15 history the EA needs.
All functions return dict(trades, open, pending) from the research-identical logic (mt5_ea/live/eas/*).
"""
from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from .eas import a as A_, c as C_, ds as DS, j2 as J2, l as L_, nt as NT, q as Q, rm as RM, rsi2 as M, rt as RT, s as S_, tl as TL
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
    weekly: bool = False               # needs the broker's W1 bars (F.W1)


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
    EA('J2@USDJPY', 'USDJPY', lambda F, env: J2.run(F, **J2.ADOPTED['USDJPY']), weekly=True),   # 2026-11-04: weekly trend, no hour window
    EA('S@XAUUSD', 'XAUUSD', lambda F, env: S_.run(F, *S_.ADOPTED['XAUUSD']), weight_choices=(0.5, 1.0)),
    EA('S@BTCUSD', 'BTCUSD', lambda F, env: S_.run(F, *S_.ADOPTED['BTCUSD']), entry_ok=weekdays),
    EA('Q@XAUUSD', 'XAUUSD', lambda F, env: Q.run(F, *Q.ADOPTED['XAUUSD'], run_max=Q.RUN_MAX['XAUUSD']), weight_choices=(0.5, 1.0)),
    EA('Q@XAGUSD', 'XAGUSD', lambda F, env: Q.run(F, *Q.ADOPTED['XAGUSD'], run_max=Q.RUN_MAX['XAGUSD'])),   # 2026-11-07: common Q setting, no H4 gate
    EA('Q@US30', 'US30', gate(lambda F, env: Q.run(F, *Q.ADOPTED['US30']), 'open')),   # off in the app from 2026-11-07 (kept for the magic numbers)
    EA('M@US30', 'US30', lambda F, env: M.run(F, **M.ADOPTED['US30'])),
    EA('M@US500', 'US500', lambda F, env: M.run(F, **M.ADOPTED['US500'])),
    EA('DS@JP225', 'JP225', gate(lambda F, env: DS.run_adopted(F, 'JP225'), 'open')),
    EA('DS@US500', 'US500', lambda F, env: DS.run_adopted(F, 'US500')),
    EA('DS@XAUUSD', 'XAUUSD', lambda F, env: DS.run_adopted(F, 'XAUUSD')),
    # P: new trend EA (2026-11-02): appended at the end so the existing magic numbers stay the same
    EA('P@XAUUSD', 'XAUUSD', lambda F, env: NT.run(F, 'XAUUSD'), window_days=800, warm_days=400),
    EA('P@EURUSD', 'EURUSD', lambda F, env: NT.run(F, 'EURUSD'), window_days=800, warm_days=400),
    EA('P@USDJPY', 'USDJPY', lambda F, env: NT.run(F, 'USDJPY'), weight_choices=(0.5, 1.0), window_days=800, warm_days=400),   # half lot selectable in the app
    # RM: return move after a long H4 trend (2026-11-03), appended at the end so the magic numbers stay the same
    EA('RM@EURUSD', 'EURUSD', lambda F, env: RM.run(F), window_days=800, warm_days=400),
    EA('RM@XAUUSD', 'XAUUSD', lambda F, env: RM.run(F), window_days=800, warm_days=400),
    # P on US indices (2026-11-04, RESEARCH_LOG §176): same rules as P@XAUUSD etc. (half lot selectable in the app; the user decides)
    EA('P@US500', 'US500', lambda F, env: NT.run(F, 'US500'), weight_choices=(0.5, 1.0), window_days=800, warm_days=400),
    EA('P@US100', 'US100', lambda F, env: NT.run(F, 'US100'), weight_choices=(0.5, 1.0), window_days=800, warm_days=400),
    # 2026-11-07 (docs/OPEN_ITEMS.md, the user's chart checks): trendline EAs and Q on BTC, appended so the magic numbers stay the same
    EA('DL@EURUSD', 'EURUSD', lambda F, env: TL.run_daily(F), window_days=1100, warm_days=750),     # daily-line zone
    EA('DL@USDJPY', 'USDJPY', lambda F, env: TL.run_daily(F), window_days=1100, warm_days=750),
    EA('HL@EURUSD', 'EURUSD', lambda F, env: TL.run_h4(F), window_days=800, warm_days=400),        # H4 trendline (L / L2 rebuilt)
    EA('Q@BTCUSD', 'BTCUSD', lambda F, env: Q.run(F, *Q.ADOPTED['BTCUSD'], run_max=Q.RUN_MAX['BTCUSD'])),
]
BY_KEY = {e.key: e for e in ADOPTED}
SYMBOLS = sorted({e.symbol for e in ADOPTED})
assert len(ADOPTED) == 30
