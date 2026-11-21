"""Trend arrows for the pair tab (pair_env.py) on stored EURUSD M15 history, through a fake broker (400 days of M15 only).
Usage: python -m mt5_ea.live.tests.test_pair_env"""
import time
from types import SimpleNamespace as NS

import pandas as pd

from mt5_ea.live import pair_env

SRC = 'research/datasets/derived/eurusd_m15/2026-10-19/EURUSD_M15_2003_2026.csv.gz'


def main():
    m = pd.read_csv(SRC); m.columns = ['t', 'o', 'h', 'l', 'c']; m['t'] = pd.to_datetime(m.t)
    asked = []

    def bars(sym, days):
        asked.append(days)
        if sym != 'EURUSD':
            raise RuntimeError(f'{sym}: symbol not found on this account')
        return m[m.t >= m.t.iat[-1] - pd.Timedelta(days=days)].reset_index(drop=True)
    t0 = time.time(); rows = pair_env.scan(NS(bars=bars), ('EURUSD', 'XXXYYY'), log=print, timeout=30)
    print(rows, f'{time.time() - t0:.1f}s')
    assert len(rows) == 1 and all(rows[0][k] in ('↑', '↓', '→') for k in ('D1', 'H4', 'H1')) and 'W1' not in rows[0]
    assert max(asked) <= 400, 'never more than 400 days of history'
    print('OK')


if __name__ == '__main__':
    main()
