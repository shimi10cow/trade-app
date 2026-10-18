"""Causal 2-point trendline candidates, v2 (fitted to the user's hand-drawn lines, 2026-10-18).

Rules (labels/TRENDLINE_EVAL_20261018.md):
  - Both points are confirmed Dow pivots of the same kind (lows -> rising line, highs -> falling line).
  - B is the newest pivot; A is one of the previous same-kind pivots, skipping at most MAX_SKIP pivots.
  - At least MIN_GAP bars between A and B.
  - No CLOSE beyond the line between A and B (wicks may pierce), tolerance CLOSE_TOL x ATR.
  - Tier 'main' = A is the outermost high/low of the leg (over [A - gap, B]) and no pivot skipped;
    otherwise 'sub'. The user's lines are mostly 'main' on W1/D1/H4.
Output: append-only create / revise / retire events (same shape as chart_lab generator) with
available_idx = bar whose close made the line known (B's confirmation or relocation bar).
"""
import numpy as np
from .pivots import pivot_events, atr

MIN_GAP = 6
MAX_SKIP = 2
CLOSE_TOL = 0.05


def candidates_for_b(b, same, c, h, l, a):
    """All lines ending at pivot b (dict id, kind, idx, price), given earlier same-kind pivots."""
    out = {}
    k = b['kind']
    prev = same[-(MAX_SKIP + 1):]
    for skip, A in enumerate(reversed(prev)):
        i1, p1, i2, p2 = A['idx'], A['price'], b['idx'], b['price']
        if i2 - i1 < MIN_GAP:
            continue
        if (k == 'lo' and p2 <= p1) or (k == 'hi' and p2 >= p1):
            continue
        mid = np.arange(i1 + 1, i2)
        if len(mid):
            line = p1 + (p2 - p1) * (mid - i1) / (i2 - i1)
            v = (line - c[mid]) / a[mid] if k == 'lo' else (c[mid] - line) / a[mid]
            if v.max() > CLOSE_TOL:
                continue
        g = i2 - i1
        w0 = max(0, i1 - g)
        a_ext = bool(h[w0:i2 + 1].max() <= p1 + 1e-12) if k == 'hi' else bool(l[w0:i2 + 1].min() >= p1 - 1e-12)
        tier = 'main' if (a_ext and skip == 0) else 'sub'
        key = f"v2:{k}:{A['id']}:{b['id']}"
        out[key] = dict(anchor_idx=int(i1), end_idx=int(i2), anchor_price=float(p1), end_price=float(p2),
                        kind=k, skip=skip, a_ext=a_ext, tier=tier, move_atr=float(abs(p2 - p1) / a[i2]))
    return out


def generate(df, tf=None, pivot_stream=None):
    c, h, l = (df[z].to_numpy(float) for z in ('c', 'h', 'l'))
    a = atr(df)
    if pivot_stream is None:
        pivot_stream = pivot_events(df)
    piv, order = {}, []
    active, out, seq = {}, [], 0

    def emit(now, action, key, cand=None):
        nonlocal seq
        seq += 1
        e = dict(event_id=seq, action=action, key=key, type='two', tf=tf, available_idx=now)
        if cand:
            e.update(cand)
        else:
            e['kind'] = active[key]['kind']
        out.append(e)

    for ev in pivot_stream:
        now = ev['available_idx']
        if ev['id'] not in piv:
            order.append(ev['id'])
        piv[ev['id']] = dict(id=ev['id'], kind=ev['kind'], idx=ev['idx'], price=ev['price'])
        b = piv[ev['id']]
        same = [piv[i] for i in order if piv[i]['kind'] == b['kind'] and i != b['id']]
        new = candidates_for_b(b, same, c, h, l, a)
        old = {k for k in active if k.endswith(f":{b['id']}") and k.startswith(f"v2:{b['kind']}:")}
        for k in sorted(old - set(new)):
            emit(now, 'retire', k)
            del active[k]
        for k, cand in new.items():
            if k not in active:
                emit(now, 'create', k, cand); active[k] = cand
            elif active[k] != cand:
                emit(now, 'revise', k, cand); active[k] = cand
    return out
