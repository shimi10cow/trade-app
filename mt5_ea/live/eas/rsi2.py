"""RSI(2) short pullback in an uptrend (M), ported from research/dow_strategy/idx_rsi2.py (2026-10-24).

D1 bars from the broker M15 (day = broker date, weekdays only). Long only. Adopted: M_200_10_ma5_st on US30 and US500.
Entry at the D1 close when close > SMA200 and RSI(2) < 10. Exit at a D1 close above SMA5; stop 2.5 x ATR(D1, 14) below the
entry (filled at min(stop, open) on a gap); at most 30 days. R = move / (2.5 x ATR) - 2 x cost / risk.
Live note: the research fills at the D1 close itself; live has to send the order just before the session closes (or at the
next open), so live fills differ a little from the backtest.
"""
import numpy as np
import pandas as pd

from ..core import Frames

ADOPTED = {'US30': dict(tr=200, lo=10, ex='ma5', st='st'), 'US500': dict(tr=200, lo=10, ex='ma5', st='st')}


def daily(F: Frames, every_day=False):
    m = pd.DataFrame(dict(o=F.o, h=F.h, l=F.l, c=F.c), index=pd.DatetimeIndex(F.T15))
    D = m.resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna()
    return D if every_day else D[D.index.dayofweek < 5]


def run(F: Frames, tr=200, lo=10, ex='ma5', st='st', every_day=False):
    """Returns dict(trades=closed trades, open=[position still open at the last D1 close], pending=[entry to take now])."""
    D = daily(F, every_day)
    c = D.c; dlt = c.diff(); up = dlt.clip(lower=0).ewm(alpha=1 / 2).mean(); dn = (-dlt.clip(upper=0)).ewm(alpha=1 / 2).mean()
    rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
    pc = c.shift(); atr = np.maximum(D.h - D.l, np.maximum((D.h - pc).abs(), (D.l - pc).abs())).rolling(14).mean()
    ma5 = c.rolling(5).mean(); MA = c.rolling(tr).mean()
    out, opened, pending = [], [], []
    i = 0; idx = D.index; n = len(D)
    while i < n:
        if idx[i] < F.START or not (c.iloc[i] > MA.iloc[i] and rsi.iloc[i] < lo and np.isfinite(atr.iloc[i])):
            i += 1; continue
        en = c.iloc[i]; risk = 2.5 * atr.iloc[i]; stp = en - risk; xp = None
        if i == n - 1:                     # signal on the last closed day: enter now (live only)
            pending.append(dict(signal_t=idx[i], side=1, entry_ref=en, sl=stp, risk=risk)); break
        j = i
        for j in range(i + 1, min(i + 30, n)):
            if st == 'st' and D.l.iloc[j] <= stp: xp = min(stp, D.o.iloc[j]); break
            done = (c.iloc[j] > ma5.iloc[j]) if ex == 'ma5' else (rsi.iloc[j] > 70) if ex == 'rsi70' else (j - i >= 5)
            if done: xp = c.iloc[j]; break
        if xp is None and j == n - 1 and j - i < 29:   # still open at the last bar (live): hold, stop at stp
            opened.append(dict(t=idx[i] + pd.Timedelta('1D'), side=1, entry=en, sl=stp, sl0=stp, risk=risk, days=j - i)); break
        if xp is None: xp = c.iloc[j]
        out.append(dict(t=idx[i] + pd.Timedelta('1D'), exit_t=idx[j] + pd.Timedelta('1D'), side=1, entry=en, risk=risk, exit=xp,
                        sl0=stp, R=(xp - en) / risk - 2 * F.COST / risk))
        i = j + 1
    return dict(trades=pd.DataFrame(out), open=opened, pending=pending)
