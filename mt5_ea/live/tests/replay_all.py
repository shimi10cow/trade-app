"""Replay the 19 adopted EAs with the live code over the research data and compare with the research trade table
(feat/final_trades.pkl, column R0 = before the swap / entry-bar / calendar corrections) (2026-10-24).

Per EA: number of trades and total R from the live code (entry-bar check OFF, like the research files) vs R0.
Gold / silver / indices / BTC research R0 was re-costed by new_summary.load, so the totals can differ by the cost; the trade
counts and entry times must match.
Usage: python -m mt5_ea.live.tests.replay_all [KEY ...]
"""
import sys

import pandas as pd

from mt5_ea.live.tests.parity import WS, ws_data, full_frames
from mt5_ea.live.env import Env
from mt5_ea.live import registry as REG
from mt5_ea.live.eas import a as A_, c as C_, ds as DS, j2 as J2, l as L_, q as Q, rsi2 as M, rt as RT, s as S_
from mt5_ea.live.eas.wave import axis_filter

# same functions as the registry, entry-bar check OFF (= research files)
RUN = {
    'R@EURUSD': lambda F, env: RT.run(F, 'R2c', env=env),
    'T2@EURUSD': lambda F, env: axis_filter(F, RT.run(F, 'T1t', env=env)),
    'T@US30': lambda F, env: RT.run(F, 'T1t', env=env),
    'L@EURUSD': lambda F, env: L_.run(F, env=env, entry_bar=False),
    'L2@XAUUSD': lambda F, env: L_.run(F, room=1.0, env=env, entry_bar=False),
    'A@EURUSD': lambda F, env: A_.run(F, env=env, entry_bar=False),
    'C@EURUSD': lambda F, env: C_.run(F, env=env, entry_bar=False),
    'C@USDJPY': lambda F, env: C_.run(F, strength=True, env=env, entry_bar=False),
    'J2@USDJPY': lambda F, env: J2.run(F, **J2.ADOPTED['USDJPY'], entry_bar=False),
    'S@XAUUSD': lambda F, env: S_.run(F, *S_.ADOPTED['XAUUSD'], entry_bar=False),
    'S@BTCUSD': lambda F, env: S_.run(F, *S_.ADOPTED['BTCUSD'], entry_bar=False),
    'Q@XAUUSD': lambda F, env: Q.run(F, *Q.ADOPTED['XAUUSD'], entry_bar=False),
    'Q@XAGUSD': lambda F, env: Q.run(F, *Q.ADOPTED['XAGUSD'], entry_bar=False),
    'Q@US30': lambda F, env: Q.run(F, *Q.ADOPTED['US30'], entry_bar=False),
    'M@US30': lambda F, env: M.run(F, **M.ADOPTED['US30']),
    'M@US500': lambda F, env: M.run(F, **M.ADOPTED['US500']),
    'DS@JP225': lambda F, env: DS.run_adopted(F, 'JP225', entry_bar=False),
    'DS@US500': lambda F, env: DS.run_adopted(F, 'US500', entry_bar=False),
    'DS@XAUUSD': lambda F, env: DS.run_adopted(F, 'XAUUSD', entry_bar=False),
}
DATA = {'J2@USDJPY': 'USDJPY100'}       # J2 research ran on prices / 100


def main(keys):
    X = pd.read_pickle(WS / 'feat/final_trades.pkl')
    rows = []
    for key in keys:
        sym = DATA.get(key, REG.BY_KEY[key].symbol)
        m, start, _ = ws_data(sym)
        F = full_frames(sym, m, start); env = Env(m)
        tr = RUN[key](F, env)['trades']
        tr = tr[pd.to_datetime(tr.t) >= pd.Timestamp('2005-01-01')]
        if key == 'S@BTCUSD':
            tr = tr[pd.to_datetime(tr.t).dt.dayofweek < 5]
        ref = X[X.key == key]
        common = len(set(pd.to_datetime(tr.t)) & set(pd.to_datetime(ref.tt)))
        rows.append(dict(EA=key, live_n=len(tr), research_n=len(ref), same_entry_time=common, live_R=round(tr.R.sum(), 1), research_R0=round(ref.R0.sum(), 1)))
        print(rows[-1], flush=True)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == '__main__':
    main(sys.argv[1:] or [e.key for e in REG.ADOPTED])
