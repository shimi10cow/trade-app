"""Live core: the shared frames every EA reads, built from one symbol's M15 bars (2026-10-24).

Same numbers as the research workspaces (research/dow_strategy/dow_turn_ea.py + ea_core.py):
  - M15 bars in broker time (XM server time), prices in the research price space
    (FX as quoted; USDJPY / 100; gold, silver, indices, crypto as natural log rounded to 6 decimals)
  - H1 / H4 / D1 = M15 resampled with label='left', closed='left' (env_recognition.data.load 'long')
  - Dow runs (env_recognition.dow_trend.run) on each frame; ATR = env_recognition.pivots.atr
Built on a recent window only: the Dow machines agree with the full-history run after 100-200 bars
(research/dow_strategy/dow_window_test.py), so `start` must leave enough warm-up before the first tradable bar.
"""
import bisect
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RESEARCH = Path(__file__).resolve().parents[2] / 'research'
if str(RESEARCH) not in sys.path:
    sys.path.insert(0, str(RESEARCH))
from env_recognition import dow_trend  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402

TF_LEN = {'D1': pd.Timedelta(days=1), 'H4': pd.Timedelta(hours=4), 'H1': pd.Timedelta(hours=1), 'M15': pd.Timedelta(minutes=15)}
PIP = 1e-4
COST = 1.2e-4        # cost per trade in price-space units, as in the research engines

LOG_SYMBOLS = {'XAUUSD', 'XAGUSD', 'US30', 'US500', 'JP225', 'BTCUSD', 'ETHUSD'}
DIV100_SYMBOLS = {'USDJPY'}


def to_space(sym, px):
    """Broker price -> research price space."""
    px = np.asarray(px, float)
    if sym in LOG_SYMBOLS:
        return np.round(np.log(px), 6)
    if sym in DIV100_SYMBOLS:
        return px / 100.0
    return px


def from_space(sym, v):
    """Research price space -> broker price."""
    v = np.asarray(v, float)
    if sym in LOG_SYMBOLS:
        return np.exp(v)
    if sym in DIV100_SYMBOLS:
        return v * 100.0
    return v


def resample(m15, tf):
    rule = {'H1': '1h', 'H4': '4h', 'D1': '1D'}[tf]
    x = m15.set_index('t').resample(rule, label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna()
    return x.reset_index()


class Frames:
    """Everything the EAs share for one symbol, from M15 bars (columns t, o, h, l, c in the research price space).

    h4_from / h1_from / m15_from: the research engines start their frames at START - 400 days (H4, H1) and
    START - 30 days (M15); the same offsets are used here so a full-history run matches the research files.
    start: first bar on which a new trade may be entered (earlier bars only warm up the state)."""

    def __init__(self, m15, start, h_days=400, m_days=30):
        m15 = m15[['t', 'o', 'h', 'l', 'c']].copy()
        m15['t'] = pd.to_datetime(m15.t)
        m15 = m15.drop_duplicates('t').sort_values('t').reset_index(drop=True)
        self.START = pd.Timestamp(start)
        self.m15_all = m15                      # every bar given (env filters use the whole window, like research env_ctx)
        cut_h = self.START - pd.Timedelta(days=h_days)
        self.h4 = resample(m15, 'H4'); self.h4 = self.h4[self.h4.t >= cut_h].reset_index(drop=True)
        self.h1 = resample(m15, 'H1'); self.h1 = self.h1[self.h1.t >= cut_h].reset_index(drop=True)
        self.m15 = m15[m15.t >= self.START - pd.Timedelta(days=m_days)].reset_index(drop=True)
        self.R4 = dow_trend.run(self.h4, 'H4')
        self.R1 = dow_trend.run(self.h1, 'H1')
        self.R15 = dow_trend.run(self.m15, 'M15')
        self.C4 = list(pd.to_datetime(self.h4.t) + TF_LEN['H4'])
        self.C1 = list(pd.to_datetime(self.h1.t) + TF_LEN['H1'])
        self.T15 = pd.to_datetime(self.m15.t)
        self.o, self.h, self.l, self.c = (self.m15[z].to_numpy(float) for z in 'ohlc')
        self.A1 = atr(self.h1)
        self.H1P = sorted(((self.C1[e['available_idx']], e['kind'], e['price']) for e in self.R1['pivot_events']), key=lambda x: x[0])
        self.H1PT = [x[0] for x in self.H1P]
        self.PIP, self.COST = PIP, COST
        # ea_core derived
        L15 = TF_LEN['M15']
        self.M15T = self.T15; self.N = len(self.T15); self.L15 = L15; self.CL15 = self.T15 + L15
        self.P15 = sorted(((self.T15[e['available_idx']] + L15, e['kind'], e['price']) for e in self.R15['pivot_events']), key=lambda x: x[0])
        self.P15T = [x[0] for x in self.P15]
        self.H4P = sorted(((self.C4[e['available_idx']], e['kind'], e['price']) for e in self.R4['pivot_events']), key=lambda x: x[0])
        self.H4PT = [x[0] for x in self.H4P]
        self.H1MA = {n: self.h1.c.rolling(n).mean().to_numpy() for n in (20, 75, 200)}

    @staticmethod
    def last_swing(P, PT, ts, kind):
        j = bisect.bisect_right(PT, ts) - 1
        while j >= 0 and P[j][1] != kind:
            j -= 1
        return P[j][2] if j >= 0 else None
