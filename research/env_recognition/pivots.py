"""Causal Dow pivot event stream (v2, simplified 2026-10-18 with user).

Rule (all timeframes identical):
  threshold = 1.9 x ATR7 (Wilder).  No ER trend adjustment, no per-timeframe multipliers
  (scored against the user's hand-labelled swings: equal or better, see labels/EVAL_20261018.md).
  Outside-bar split ON (bullish bar = low first, bearish = high first).
The frozen v1 detector (dow_frozen_v1) is kept untouched for comparison only.

Each event: dict(action='confirm'|'relocate', id, kind 'hi'|'lo', idx (anchor bar),
price (wick), available_idx (bar whose close makes it known)).
"""
import numpy as np
import pandas as pd

ATR_PERIOD = 7
K = 1.9


def atr(df, period=ATR_PERIOD):
    h, l, c = (df[z].to_numpy(float) for z in ('h', 'l', 'c'))
    pc = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    tr[0] = h[0] - l[0]
    return pd.Series(tr).ewm(alpha=1 / period, adjust=False).mean().to_numpy()


def indicators(df, tf=None, k=K):
    a = atr(df)
    return a, k * a


def pivot_events(df, tf=None, start=60, th=None, outside_bar=True):
    """outside_bar=True: a bar that makes a new extreme of the current leg AND exceeds the previous
    opposite pivot is split by candle colour (bullish = low first, bearish = high first): the new
    extreme is confirmed on that bar instead of relocating the previous pivot."""
    o = df['o'].to_numpy(float)
    h, l, c = (df[z].to_numpy(float) for z in ('h', 'l', 'c'))
    if th is None:
        _, th = indicators(df, tf)
    direction = 0; ei = start; ep = c[start]; last = -1
    ps = []; ev = []

    def emit(action, p, i):
        ev.append(dict(action=action, id=p['id'], kind=p['kind'], idx=p['idx'],
                       price=p['price'], available_idx=i))

    for i in range(start + 1, len(df)):
        t = th[i]
        if direction == 0:
            if h[i] > c[start] + t:
                direction, ei, ep = 1, i, h[i]
            elif l[i] < c[start] - t:
                direction, ei, ep = -1, i, l[i]
            continue
        if direction == 1:
            if h[i] >= ep:
                ep, ei = h[i], i
            if i > ei and ep - l[i] >= t and ei > last:
                p = dict(id=len(ps), kind='hi', idx=int(ei), price=float(h[ei]))
                ps.append(p); emit('confirm', p, i)
                last, direction, ei, ep = ei, -1, i, l[i]
        else:
            if l[i] <= ep:
                ep, ei = l[i], i
            if i > ei and h[i] - ep >= t and ei > last:
                p = dict(id=len(ps), kind='lo', idx=int(ei), price=float(l[ei]))
                ps.append(p); emit('confirm', p, i)
                last, direction, ei, ep = ei, 1, i, h[i]
        if outside_bar and ps:
            # falling leg made its new low on this bar, bar is bullish and closes the bar above prior high
            if direction == -1 and ei == i and ps[-1]['kind'] == 'hi' and h[i] > ps[-1]['price'] and c[i] >= o[i]:
                p = dict(id=len(ps), kind='lo', idx=int(i), price=float(l[i]))
                ps.append(p); emit('confirm', p, i)
                last, direction, ei, ep = i, 1, i, h[i]
                continue
            if direction == 1 and ei == i and ps[-1]['kind'] == 'lo' and l[i] < ps[-1]['price'] and c[i] < o[i]:
                p = dict(id=len(ps), kind='hi', idx=int(i), price=float(h[i]))
                ps.append(p); emit('confirm', p, i)
                last, direction, ei, ep = i, -1, i, l[i]
                continue
        if ps and direction == -1 and ps[-1]['kind'] == 'hi' and h[i] > ps[-1]['price']:
            p = ps[-1]; p['idx'] = i; p['price'] = float(h[i]); emit('relocate', p, i)
            last, ei, ep = i, i, l[i]
        elif ps and direction == 1 and ps[-1]['kind'] == 'lo' and l[i] < ps[-1]['price']:
            p = ps[-1]; p['idx'] = i; p['price'] = float(l[i]); emit('relocate', p, i)
            last, ei, ep = i, i, h[i]
    return ev


def final_pivots(events):
    """Hindsight table (last version of every pivot). For display only, never for signals."""
    piv = {}
    for e in events:
        piv[e['id']] = e
    return [piv[k] for k in sorted(piv)]
