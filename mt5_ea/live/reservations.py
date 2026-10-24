"""Reservation entries (予約エントリー, 2026-10-24, docs/EA_SYSTEM_PLAN.md).

The trader analyses a pair by hand and reserves the entry in the app; the EA PC enters automatically when the stochastic
trigger fires. Same trigger as the old EA (Stochastic 14,5,3 on M15 or H1):
  buy : %K goes below 20 -> %K crosses above %D -> %K crosses back above 20   (entry at that bar's close)
  sell: %K goes above 80 -> %K crosses below %D -> %K crosses back below 80
Only bars after the reservation was made count, and only a trigger on the last closed bar is traded (no late entries after
the PC was off; the state machine simply continues and waits for the next trigger).
Stop (chosen in the app): stoch = just outside the pullback extreme since %K entered the 20/80 zone (0.1 ATR(14) of that frame);
m15ma200 / h1ma75 / h1ma200 = that moving average at entry (on the wrong side of the price -> stoch instead).
Target: the price given in the app, or none (exit by stop or by hand in MT5).
Lot: per reservation, 'pct' (% of equity at risk), 'jpy' (max loss in yen) or 'lot' (fixed lots).
"""
import math

import numpy as np
import pandas as pd

RES_MAGIC = 780000
SERVER_TZ = 'Europe/Athens'
MAX_MINLOT_RISK = 0.015


def to_server(jst_text):
    """'2026-10-24 21:15+09:00' (or without offset = Japan time) -> naive broker time."""
    t = pd.Timestamp(str(jst_text).strip().replace('/', '-'))
    if t.tzinfo is None:
        t = t.tz_localize('Asia/Tokyo')
    return t.tz_convert(SERVER_TZ).tz_localize(None)


def h1_bars(m15):
    """Complete H1 bars from M15 bars (t = hour start, broker time)."""
    d = m15.set_index('t')
    g = d.groupby(d.index.floor('h'))
    out = pd.DataFrame(dict(o=g.o.first(), h=g.h.max(), l=g.l.min(), c=g.c.last(), n=g.c.size())).reset_index()
    out = out[out.n == 4].drop(columns='n').rename(columns=dict(index='t'))
    out.columns = ['t', 'o', 'h', 'l', 'c']
    return out.reset_index(drop=True)


def stoch(h, l, c, n=14, k_s=5, d_s=3):
    hh = pd.Series(h).rolling(n).max(); ll = pd.Series(l).rolling(n).min(); c = pd.Series(c)
    raw = np.where(hh == ll, 50.0, (c - ll) / (hh - ll) * 100.0)
    raw = pd.Series(raw).where(hh.notna())
    k = raw.rolling(k_s).mean(); d = k.rolling(d_s).mean()
    return k.to_numpy(), d.to_numpy()


def atr(h, l, c, n=14):
    h, l, c = map(np.asarray, (h, l, c))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().to_numpy()


def trigger_on_last(bars, side, since):
    """bars: closed bars of the trigger frame (t, o, h, l, c). Returns None, or dict(extreme, atr) when the trigger fires
    on the last bar. Only bars with t >= since are used for the state machine (the indicator uses the earlier bars too)."""
    if len(bars) < 30:
        return None
    k, d = stoch(bars.h.to_numpy(), bars.l.to_numpy(), bars.c.to_numpy())
    a = atr(bars.h, bars.l, bars.c)
    i0 = int(np.searchsorted(bars.t.to_numpy(), np.datetime64(pd.Timestamp(since))))
    i0 = max(i0, 1)
    state, ext, last = 0, None, len(bars) - 1
    zone, out_of = (20.0, 1) if side == 1 else (80.0, -1)
    for i in range(i0, len(bars)):
        pk, pd_, kk, dd = k[i - 1], d[i - 1], k[i], d[i]
        if np.isnan([pk, pd_, kk, dd]).any():
            continue
        lo, hi = bars.l.iat[i], bars.h.iat[i]
        if state >= 1:
            ext = min(ext, lo) if side == 1 else max(ext, hi)
        if state == 0 and side * (zone - kk) > 0:                    # buy: K < 20 / sell: K > 80
            state, ext = 1, (lo if side == 1 else hi)
        elif state == 1 and side * (pk - pd_) <= 0 and side * (kk - dd) > 0:      # K crosses D in the trade direction
            state = 2
        elif state == 2 and side * (zone - pk) >= 0 and side * (kk - zone) > 0:   # K leaves the zone
            if i == last:
                return dict(extreme=float(ext), atr=float(a[i]) if not np.isnan(a[i]) else 0.0, t=bars.t.iat[i])
            state, ext = 0, None
    return None


def mas(m15):
    """Moving averages for the stop choices, from closed M15 bars."""
    h1 = h1_bars(m15)
    sma = lambda x, n: float(x.iloc[-n:].mean()) if len(x) >= n else None
    return dict(m15ma200=sma(m15.c, 200), h1ma75=sma(h1.c, 75), h1ma200=sma(h1.c, 200))


def stop_for(mode, side, price, hit, sl_price=None):
    """Returns (stop price, note)."""
    if str(sl_price or '').strip() and not mode:                # old reservations with a price
        return float(sl_price), ''
    stoch = hit['extreme'] - side * 0.1 * hit['atr']
    if mode in ('m15ma200', 'h1ma75', 'h1ma200'):
        v = (hit.get('mas') or {}).get(mode)
        if v is not None and side * (price - v) > 0:
            return float(v), ''
        return stoch, ' / MA が逆側なのでストキャス直下'
    return stoch, ''


def lots_for_res(spec, equity, mode, value, stop_dist):
    """Returns (lots, risk_money, note). lots = 0 means skip."""
    per_lot = spec.loss_per_lot(stop_dist)
    if stop_dist <= 0 or per_lot <= 0:
        return 0.0, 0.0, 'bad stop'
    value = float(value or 0)
    if mode == 'lot':
        lots = math.floor(value / spec.volume_step + 1e-9) * spec.volume_step
        lots = min(max(lots, spec.volume_min), spec.volume_max)
        return round(lots, 8), lots * per_lot, f'{lots} lot（指定）'
    money = equity * value / 100.0 if mode == 'pct' else value
    lots = min(math.floor(money / per_lot / spec.volume_step + 1e-9) * spec.volume_step, spec.volume_max)
    if lots < spec.volume_min:
        if spec.volume_min * per_lot <= MAX_MINLOT_RISK * equity:
            return spec.volume_min, spec.volume_min * per_lot, 'min lot'
        return 0.0, spec.volume_min * per_lot, f'skip: min lot risk {spec.volume_min * per_lot / equity:.2%} > 1.5%'
    return round(lots, 8), lots * per_lot, ('risk %.2f%%' % value) if mode == 'pct' else f'max loss {value:.0f}'
