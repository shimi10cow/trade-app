"""CA: AUDJPY-only C (correction line break with the H4 Dow trend), 2026-11-08 (docs/OPEN_ITEMS.md "2026-11-08 の決定"; research
scratch a5..a17, the user's AUDJPY chart checks).

AUDJPY moves with its H4 Dow trend: C setups against the H4 major trend lost (-0.19R over 20 years) and late trends (5th leg and
later) lost too, while the H1 often turns against the trend and comes back above the H4 pullback low (deep pullbacks).
  Entry : C's setup (eas/c.py events: a correction line after an M15 impulse, close beyond it) and an M15 provisional turn within 4 h
  Trend : the H4 major Dow trend points the trade's way at its 1st..4th leg (eas/j2.h4_legs at the setup time)
  Env   : the daily side (H4 close beyond H4 SMA1200 = daily SMA200, as C on EURUSD / USDJPY) and no H4 triangle forming
  Stop  : the M15 turn swing + 1.0 ATR(H1)
  Exit  : until +1.5R only an H4 close below the latest H4 swing low formed after the entry (engine cfg h4sw=0); from +1.5R the
          M15 swing trail (sells mirrored)
Not used (tested, kept trades as good as the removed ones): H1 Dow way, H4 stretch from SMA75, H1 SMA75 distance, weekly trend,
H4 volatility, hour of day, C's EURUSD / USDJPY extras (H1 run, H4 MA opening, line strength).
Research (research data -> server time, 2005-01 .. 2026-10, cost 1.5 pips, KIWAMI swap-free): 231 trades (10.6/yr), win 48%,
+0.25R, PF 1.49, max DD 7.4R, both halves + (+0.13 / +0.35), top 5% excluded +0.07. With the 27 app EAs (2017-07..): monthly
correlation -0.05, +0.58R a month in their worst 20% of months; 1% risk 233% -> 247% a year, max DD 19.1% -> 19.0%.
"""
from .. import engine as E
from ..core import Frames
from ..env import Env
from . import c as C_
from .j2 import h4_legs

CFG = dict(trig='dow', stop='m15turn', buf=1.0, win=4, exit='m15', act=1.5, h4sw=0.0, dside=0, notri='H4')
LEGS = (1, 4)


def events(F: Frames):
    legs = h4_legs(F); out = []
    for e in C_.events(F):
        lg = legs(e['t'], e['side'])
        if LEGS[0] <= lg <= LEGS[1]:
            out.append(dict(e, tag=f"{e['tag']}|L{lg}"))
    return out


def run(F: Frames, env=None, entry_bar=True):
    env = env or Env(F.m15_all)
    return E.run(F, events(F), CFG, env_ok=env.ok, entry_bar=entry_bar)
