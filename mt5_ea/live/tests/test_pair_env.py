"""Trend arrows for the pair tab (pair_env.py) on stored EURUSD M15 history, through a fake MT5 that serves MN1/W1/D1/H4/H1.
Usage: python -m mt5_ea.live.tests.test_pair_env"""
import time
from types import SimpleNamespace as NS

import pandas as pd

from mt5_ea.live import pair_env

SRC = 'research/datasets/derived/eurusd_m15/2026-10-19/EURUSD_M15_2003_2026.csv.gz'
RULE = {'MN1': 'MS', 'W1': 'W-MON', 'D1': '1D', 'H4': '4h', 'H1': '1h'}


class FakeMT5:
    TIMEFRAME_MN1, TIMEFRAME_W1, TIMEFRAME_D1, TIMEFRAME_H4, TIMEFRAME_H1 = 'MN1', 'W1', 'D1', 'H4', 'H1'

    def __init__(self, m15):
        self.m = m15.set_index('t')

    def copy_rates_from_pos(self, name, tf, pos, n):
        if name != 'EURUSD':
            return None
        x = self.m.resample(RULE[tf], label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().tail(n)
        return x.reset_index().assign(time=lambda d: d.t.astype('int64') // 10**9).rename(columns=dict(o='open', h='high', l='low', c='close')).to_records()


def main():
    m = pd.read_csv(SRC)
    m.columns = [c.lower() for c in m.columns]
    tcol = next(c for c in m.columns if c in ('t', 'time', 'datetime', 'date'))
    m = m.rename(columns={tcol: 't', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c'}); m['t'] = pd.to_datetime(m.t)
    b = NS(mt5=FakeMT5(m[['t', 'o', 'h', 'l', 'c']]), name=lambda s: s)
    t0 = time.time(); rows = pair_env.scan(b, ('EURUSD', 'XXXYYY'))
    print(rows, f'{time.time() - t0:.1f}s')
    assert len(rows) == 1 and all(rows[0][k] in ('↑', '↓', '→') for k in ('M1', 'W1', 'D1', 'H4', 'H1'))
    print('OK')


if __name__ == '__main__':
    main()
