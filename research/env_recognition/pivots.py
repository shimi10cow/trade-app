"""Causal Dow pivot event stream (parity target: dow_frozen_v1/dow_final_engine.detect).

Each event: dict(action='confirm'|'relocate', id, kind 'hi'|'lo', idx (anchor bar),
price (wick), available_idx (bar whose close makes it known)).
"""
import numpy as np
import pandas as pd

PARAMS = {'W1': (7, 1.9, .15, .4), 'D1': (7, 1.9, -.15, .4),
          'H4': (7, 2.0, .30, .4), 'H1': (7, 2.4, -.15, .25),
          'M15': (7, 2.1, .30, .25)}


def indicators(df, tf):
    ap, k, boost, cut = PARAMS[tf]
    h, l, c = (df[z].to_numpy(float) for z in ('h', 'l', 'c'))
    pc = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    tr[0] = h[0] - l[0]
    atr = pd.Series(tr).ewm(alpha=1 / ap, adjust=False).mean().to_numpy()
    noise = pd.Series(abs(np.diff(c, prepend=c[0]))).rolling(20).sum().to_numpy()
    er = np.zeros(len(c))
    er[20:] = abs(c[20:] - c[:-20]) / np.maximum(noise[20:], 1e-12)
    th = k * atr * np.where(er >= cut, 1 + boost, 1)
    return atr, th


def pivot_events(df, tf, start=60, th=None):
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
