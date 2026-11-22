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
    w = m.set_index('t').resample('W-MON', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    ranges = []

    class MT5:
        TIMEFRAME_W1 = 'W1'
        def last_error(self): return (0, '')
        def copy_rates_range(self, n, tf, a, z):
            ranges.append((pd.Timestamp(a), pd.Timestamp(z)))
            x = w[(w.t >= pd.Timestamp(a)) & (w.t <= pd.Timestamp(z))]
            return x.assign(time=[int(z.timestamp()) for z in x.t]).rename(columns=dict(o='open', h='high', l='low', c='close')).to_records()
    end = m.t.iat[-1]
    orig = pair_env.weekly_bars
    pair_env.weekly_bars = lambda b, p: orig(b, p, now=end + pd.Timedelta(days=1))
    t0 = time.time(); rows = pair_env.scan(NS(bars=bars, mt5=MT5(), name=lambda s: s), ('EURUSD', 'XXXYYY'), log=print, timeout=30)
    pair_env.weekly_bars = orig
    assert all((z - a).days <= 3 * 365 + 7 for a, z in ranges), 'never more than 3 years of weekly bars'
    assert rows[0]['W1'] in ('↑', '↓', '→')
    print(rows, f'{time.time() - t0:.1f}s')
    assert len(rows) == 1 and all(rows[0][k] in ('↑', '↓', '→') for k in ('D1', 'H4', 'H1')) 
    assert max(asked) <= 400, 'never more than 400 days of history'
    print('OK')


if __name__ == '__main__':
    main()
