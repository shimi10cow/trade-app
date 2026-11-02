"""Export long price history of stock-index CFDs from MT5 for research (2026-11).

Run on the PC with the EA's demo MT5 (any XM MT5 that is logged in works; read-only, no orders):
    py -m mt5_ea.tools.export_index_bars                 # every index CFD the terminal offers (names with 'Cash')
    py -m mt5_ea.tools.export_index_bars --list          # only print the symbols it would read
    py -m mt5_ea.tools.export_index_bars --symbols GER40Cash,UK100Cash
Writes research/data/index_bars/<NAME>_D1.csv.gz and <NAME>_M15.csv.gz (broker time; time, open, high, low, close, tick_volume)
and manifest.json (first / last bar and count per file). NAME = the symbol without 'Cash' / '#'.
M15 is read in 120-day pieces from today backwards until MT5 has no more data (3 empty pieces in a row), each piece retried 3 times;
D1 the same way in 3000-day pieces. Only market prices are written (nothing about the account).
Set the terminal's 'Max bars in chart' to Unlimited first (Tools > Options > Charts), or long M15 history is cut.
"""
import argparse
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'research' / 'data' / 'index_bars'
DEFAULT_PATH = r'C:\Program Files\XMTrading MT5\terminal64.exe'


def name_of(sym):
    return sym.replace('Cash', '').replace('#', '').replace('.', '')


def read(mt5, sym, tf, piece_days):
    out, end, empty = [], datetime.utcnow() + timedelta(days=2), 0
    while empty < 3:
        start = end - timedelta(days=piece_days); got = None
        for _ in range(3):
            got = mt5.copy_rates_range(sym, tf, start, end)
            if got is not None:
                break
            time.sleep(1)
        if got is None or len(got) == 0:
            empty += 1
        else:
            empty = 0; out.append(pd.DataFrame(got))
        end = start
        if start.year < 1995:
            break
    if not out:
        return pd.DataFrame()
    d = pd.concat(out).drop_duplicates('time').sort_values('time')
    d['time'] = pd.to_datetime(d.time, unit='s')
    return d[['time', 'open', 'high', 'low', 'close', 'tick_volume']].reset_index(drop=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--path', default=DEFAULT_PATH, help='terminal64.exe of a logged-in MT5')
    ap.add_argument('--symbols', default='', help='comma separated broker symbols (default: every symbol whose name has Cash)')
    ap.add_argument('--list', action='store_true')
    a = ap.parse_args()
    import MetaTrader5 as mt5
    if not mt5.initialize(a.path):
        raise SystemExit(f'MT5 initialize failed: {mt5.last_error()}')
    syms = [s.strip() for s in a.symbols.split(',') if s.strip()] or sorted(s.name for s in (mt5.symbols_get() or []) if 'Cash' in s.name)
    print('symbols:', ', '.join(syms))
    if a.list:
        return
    OUT.mkdir(parents=True, exist_ok=True); man = {}
    for sym in syms:
        mt5.symbol_select(sym, True)
        for tf_name, tf, piece in (('D1', mt5.TIMEFRAME_D1, 3000), ('M15', mt5.TIMEFRAME_M15, 120)):
            d = read(mt5, sym, tf, piece)
            key = f'{name_of(sym)}_{tf_name}'
            if len(d):
                d.to_csv(OUT / f'{key}.csv.gz', index=False, compression='gzip')
                man[key] = dict(symbol=sym, bars=len(d), first=str(d.time.iat[0]), last=str(d.time.iat[-1]))
            else:
                man[key] = dict(symbol=sym, bars=0, error=str(mt5.last_error()))
            print(key, man[key], flush=True)
    (OUT / 'manifest.json').write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding='utf-8')
    mt5.shutdown()


if __name__ == '__main__':
    main()
