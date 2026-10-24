"""Paper run of the live runner (2026-10-24): replay recent M15 bars of one symbol bar by bar through Runner + PaperBroker,
exactly as the live loop would (orders at the price of the bar that just closed, stops checked on every new bar), and
compare the executed trades with the simulated trades of the same EAs.

Usage: python -m mt5_ea.live.tests.paper_run SYM START END [EA_KEY ...]   (dates, e.g. 2026-10-11 2026-10-17)
"""
import logging
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from mt5_ea.live.broker import PaperBroker
from mt5_ea.live.core import from_space
from mt5_ea.live.registry import ADOPTED
from mt5_ea.live.runner import MAGIC, Runner
from mt5_ea.live.sizing import SymbolSpec
from mt5_ea.live.tests.parity import WS

logging.basicConfig(level=logging.WARNING)


def raw_bars(sym):
    w = WS / f'ws_{sym}'
    m = pd.read_csv(w / 'M15_broker.csv', parse_dates=['time']).rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
    if sym in ('XAUUSD', 'XAGUSD', 'US30', 'US500', 'JP225', 'BTCUSD', 'ETHUSD'):
        for z in 'ohlc':
            m[z] = np.exp(m[z])                      # workspace prices are logs -> broker prices
    return m


def main(sym, start, end, keys):
    m = raw_bars(sym)
    eas = [e for e in ADOPTED if e.symbol == sym and (not keys or e.key in keys)]
    b = PaperBroker(balance=1_000_000.0, specs={sym: SymbolSpec(0.01, 0.01, 100.0, 0.01 if m.c.iat[-1] > 50 else 1e-5, 1.0)})
    b.set_bars(sym, m)
    tmp = Path(tempfile.mkdtemp())
    R = Runner(b, notify=lambda k, t: None, account_kind='paper', state_file=tmp / 's.json', config_file=tmp / 'c.json')
    R.set_config(dict(running=True, base_risk=0.01, eas={e.key: dict(mode='auto', weight=e.weight) for e in eas}))
    import mt5_ea.live.gas as G
    G.enqueue = lambda *a, **k: None
    steps = m[(m.t >= pd.Timestamp(start)) & (m.t < pd.Timestamp(end))].reset_index(drop=True)
    log = []
    for i, bar in steps.iterrows():
        b.now = bar.t + pd.Timedelta(minutes=15)          # this bar just closed
        b.on_bar(sym, bar)                                 # stops / targets inside this bar first
        log += R.step()
        R.sweep_closed()
    print(f'{sym}: {len(steps)} bars, actions {len(log)}, closed trades {len(b.closed)}, still open {len(b.positions())}')
    for line in log[:40]:
        print('  ', line)
    print(pd.DataFrame(b.closed)[['comment', 'side', 'open_t', 'open', 'close_t', 'close', 'why']].tail(10).to_string() if b.closed else 'no closed trades')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
