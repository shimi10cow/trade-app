"""OHLC loaders for environment-recognition research.

Sources inside the repo (no external download needed):
- chart_lab/eurusd_chart_lab_complete.html: SERIES for W1(2014-)/D1(2015-)/H4/H1/M15(2025-).
- datasets/derived/eurusd_h4_structure/2026-10-15/h4_structure_bars.csv: H4 2003-05..2026-10.
Timestamps are source-clock naive (broker timezone not verified).
"""
import json
from functools import lru_cache
from pathlib import Path
import pandas as pd

RESEARCH = Path(__file__).resolve().parents[1]
HTML = RESEARCH / 'chart_lab' / 'eurusd_chart_lab_complete.html'
H4_CSV = RESEARCH / 'datasets/derived/eurusd_h4_structure/2026-10-15/h4_structure_bars.csv'


@lru_cache(maxsize=1)
def _series():
    s = HTML.read_text(encoding='utf-8')
    return json.JSONDecoder().raw_decode(s.split('const SERIES=', 1)[1])[0]


def load_chart_series(tf):
    """OHLC exactly as embedded in the chart lab HTML (same candles the user reviewed)."""
    rows = [r[:5] for r in _series()[tf]]
    df = pd.DataFrame(rows, columns=['t', 'o', 'h', 'l', 'c'])
    df['t'] = pd.to_datetime(df.t)
    return df.reset_index(drop=True)


def load_h4_full():
    df = pd.read_csv(H4_CSV, index_col=0, parse_dates=True)
    df = df[['open', 'high', 'low', 'close']].rename(columns=dict(open='o', high='h', low='l', close='c'))
    df.index.name = 't'
    return df.reset_index()


def resample(df, rule):
    """Resample completed bars. rule: '1D' or 'W-SUN'-style. Only bars with data are kept."""
    x = df.set_index('t')
    label = 'left'
    out = x.resample(rule, label=label, closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna()
    return out.reset_index()


LONG_M15 = RESEARCH / 'datasets/derived/eurusd_m15/2026-10-19/EURUSD_M15_2003_2026.csv.gz'


@lru_cache(maxsize=1)
def load_long_m15():
    """EURUSD M15 2003-05..2026-10 (Forex Tester, UTC) converted to broker time (Europe/Athens, EET/EEST),
    which matches the chart/MT5 series (median |close diff| 0.4 pip, checked 2026-10-19)."""
    d = pd.read_csv(LONG_M15, parse_dates=['time'])
    d['time'] = d.time.dt.tz_localize('UTC').dt.tz_convert('Europe/Athens').dt.tz_localize(None)
    d = d.drop_duplicates('time').sort_values('time')
    return d.rename(columns=dict(time='t', open='o', high='h', low='l', close='c')).reset_index(drop=True)


RAW_M5 = RESEARCH / 'datasets/raw/m5'


def load_m5(sym='EURUSD'):
    """M5 2003-05..2026-10 from the user's upload (<SYM>_m1_M5.csv.gz on main, built from M1; UTC like the long M15:
    EURUSD M5 resampled to M15 matches LONG_M15 exactly on all 583,458 bars). Converted to broker time like load_long_m15."""
    d = pd.read_csv(RAW_M5 / f'{sym}_M5.csv.gz', usecols=['time', 'open', 'high', 'low', 'close'], parse_dates=['time'])
    d['time'] = d.time.dt.tz_localize('UTC').dt.tz_convert('Europe/Athens').dt.tz_localize(None)
    d = d.drop_duplicates('time').sort_values('time')
    return d.rename(columns=dict(time='t', open='o', high='h', low='l', close='c')).reset_index(drop=True)


def load(tf, source='chart'):
    if source == 'chart':
        return load_chart_series(tf)
    if source == 'full':
        h4 = load_h4_full()
        if tf == 'H4':
            return h4
        if tf == 'D1':
            return resample(h4, '1D')
        if tf == 'W1':
            w = h4.set_index('t').resample('W-MON', label='left', closed='left').agg(
                dict(o='first', h='max', l='min', c='last')).dropna()
            return w.reset_index()
    if source == 'long':
        m = load_long_m15()
        if tf == 'M15':
            return m.copy()
        rule = {'H1': '1h', 'H4': '4h', 'D1': '1D', 'W1': 'W-MON'}[tf]
        x = m.set_index('t').resample(rule, label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna()
        return x.reset_index()
    raise ValueError(f'unsupported tf/source {tf}/{source}')
