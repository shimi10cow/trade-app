"""Causal 2-point trendline candidates, v2 (fitted to the user's hand-drawn lines, 2026-10-18).

Rules (labels/TRENDLINE_EVAL_20261018.md, user review 2026-10-18):
  - Both points are confirmed Dow pivots of the same kind (lows -> rising line, highs -> falling line).
  - B is the newest pivot; A is one of the previous same-kind pivots, skipping at most MAX_SKIP pivots.
  - At least MIN_GAP bars between A and B.
  - A is the outermost wick between A and B ("covers the outside").
  - No CLOSE beyond the line between A and B (wicks may pierce), tolerance CLOSE_TOL x ATR.
  - Per B at most two lines: the one through the adjacent pivot (skip 0) and the longest one.
  - tier 'main' = skip 0 and A outermost over [A - gap, B] (strict); 'near' = skip 0; 'skip' = longest with skips.
  - Redraw: when a new line starts from the same A as an older live line, the older one is retired
    ('redrawn') by the lifecycle module (lines.py).
Output: append-only create / revise / retire events (same shape as chart_lab generator) with
available_idx = bar whose close made the line known (B's confirmation or relocation bar).
"""
import numpy as np
from .pivots import pivot_events, atr

MIN_GAP = 6
MAX_SKIP = 3
CLOSE_TOL = 0.05


def candidates_for_b(b, same, c, h, l, a, max_skip=MAX_SKIP):
    """All lines ending at pivot b (dict id, kind, idx, price), given earlier same-kind pivots."""
    out = {}
    k = b['kind']
    prev = same[-(max_skip + 1):]
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
        outer = bool(h[i1:i2 + 1].max() <= p1 + 1e-12) if k == 'hi' else bool(l[i1:i2 + 1].min() >= p1 - 1e-12)
        if not outer:
            continue
        w0 = max(0, i1 - g)
        a_ext = bool(h[w0:i2 + 1].max() <= p1 + 1e-12) if k == 'hi' else bool(l[w0:i2 + 1].min() >= p1 - 1e-12)
        tier = 'main' if (a_ext and skip == 0) else 'near' if skip == 0 else 'skip'
        key = f"v2:{k}:{A['id']}:{b['id']}"
        out[key] = dict(anchor_idx=int(i1), end_idx=int(i2), anchor_price=float(p1), end_price=float(p2),
                        kind=k, skip=skip, a_ext=a_ext, tier=tier, move_atr=float(abs(p2 - p1) / a[i2]),
                        anchor_id=A['id'])
    # keep the adjacent-pivot line and the longest line only
    keep = {kk for kk, v in out.items() if v['skip'] == 0}
    sk = [kk for kk, v in out.items() if v['skip'] > 0]
    if sk:
        keep.add(max(sk, key=lambda kk: out[kk]['end_idx'] - out[kk]['anchor_idx']))
    return {kk: out[kk] for kk in keep}


def generate(df, tf=None, pivot_stream=None, max_skip=None):
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
        new = candidates_for_b(b, same, c, h, l, a, MAX_SKIP if max_skip is None else max_skip)
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


# ---------------------------------------------------------------------------------------------
# v3 (user review 2026-10-18 #2): "wrap the big picture" - one live line per direction.
#   - New same-kind pivot B:
#       * if B sits on the current line (within TOUCH_ATR) -> keep it (3rd point confirms the line)
#       * else build A->B with A = previous same-kind pivot (skip 0); if that fails, A = the one
#         before (skip 1) allowing the middle pivot / closes to poke through by MID_TOL_ATR
#       * A must be the outermost wick between A and B
#       * the line must NOT already be broken by a close between B and the confirmation bar
#         (a steep line from a low followed by sideways drift is skipped -> next low is used)
#   - A new line replaces the previous live line of the same direction (reason 'redrawn').
# ---------------------------------------------------------------------------------------------
TOUCH_ATR = 0.3
MID_TOL_ATR = 0.3


def _line_ok(A, B, now, k, c, h, l, a, tol, skip_broken=True):
    i1, p1, i2, p2 = A['idx'], A['price'], B['idx'], B['price']
    if i2 - i1 < MIN_GAP or (k == 'lo' and p2 <= p1) or (k == 'hi' and p2 >= p1):
        return False
    outer = (h[i1:i2 + 1].max() <= p1 + 1e-12) if k == 'hi' else (l[i1:i2 + 1].min() >= p1 - 1e-12)
    if not outer:
        return False
    xs = np.arange(i1 + 1, now + 1)          # between the points AND up to the confirmation bar
    line = p1 + (p2 - p1) * (xs - i1) / (i2 - i1)
    v = (line - c[xs]) / a[xs] if k == 'lo' else (c[xs] - line) / a[xs]
    inside = xs < i2
    if inside.any() and v[inside].max() > tol:
        return False
    if skip_broken and (~inside).any() and v[~inside].max() > 0:   # already broken after B -> skip this pivot
        return False
    return True


def generate_v3(df, tf=None, pivot_stream=None, steep=False, allow_skip=False):
    """steep=True (entry timeframes, M15): keep steep lines even if broken before confirmation."""
    c, h, l = (df[z].to_numpy(float) for z in ('c', 'h', 'l'))
    a = atr(df)
    if pivot_stream is None:
        pivot_stream = pivot_events(df)
    piv, order, out = {}, [], []
    cur = {'lo': None, 'hi': None}     # live line per kind: dict(key, A, B, geometry)
    seq = 0

    def emit(now, action, key, cand=None, kind=None, reason=None):
        nonlocal seq
        seq += 1
        e = dict(event_id=seq, action=action, key=key, type='two', tf=tf, available_idx=now)
        if cand:
            e.update(cand)
        else:
            e['kind'] = kind
        if reason:
            e['reason'] = reason
        out.append(e)

    def value(ln, i):
        return ln['anchor_price'] + (ln['end_price'] - ln['anchor_price']) * (i - ln['anchor_idx']) / (ln['end_idx'] - ln['anchor_idx'])

    for ev in pivot_stream:
        now = ev['available_idx']
        if ev['id'] not in piv:
            order.append(ev['id'])
        piv[ev['id']] = dict(id=ev['id'], kind=ev['kind'], idx=ev['idx'], price=ev['price'])
        B = piv[ev['id']]
        k = B['kind']
        ln = cur[k]
        if ln is not None:
            # live line already broken by a close since it was drawn? forget it (lifecycle retires it)
            xs = np.arange(ln['end_idx'] + 1, now + 1)
            if len(xs):
                vv = np.array([value(ln, i) for i in xs])
                br = (vv - c[xs]) if k == 'lo' else (c[xs] - vv)
                if (br > 0).any():
                    cur[k] = ln = None
        if ln is not None and ln['b_id'] != B['id']:
            if abs(B['price'] - value(ln, B['idx'])) / a[B['idx']] <= TOUCH_ATR:
                ln['touches'] += 1          # 3rd point on the line: keep it
                continue
        same = [piv[i] for i in order if piv[i]['kind'] == k and i != B['id']]
        new = None
        for skip, tol in ((0, CLOSE_TOL), (1, MID_TOL_ATR))[:2 if allow_skip else 1]:
            if len(same) > skip:
                A = same[-1 - skip]
                if _line_ok(A, B, now, k, c, h, l, a, tol, skip_broken=not steep):
                    new = (A, skip)
                    break
        if new is None:
            continue
        A, skip = new
        key = f"v3:{k}:{A['id']}:{B['id']}"
        cand = dict(anchor_idx=int(A['idx']), end_idx=int(B['idx']), anchor_price=float(A['price']),
                    end_price=float(B['price']), kind=k, skip=skip, tier='main', anchor_id=A['id'])
        if ln is not None and ln['key'] != key:
            emit(now, 'retire', ln['key'], kind=k, reason='redrawn')
        emit(now, 'create' if (ln is None or ln['key'] != key) else 'revise', key, cand)
        cur[k] = dict(cand, key=key, b_id=B['id'], touches=2)
    return out
