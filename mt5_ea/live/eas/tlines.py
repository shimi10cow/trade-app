"""Trendlines for the DL (daily) and HL (H4) EAs, copied from research/dow_strategy/daily_line/lines_v4.py (2026-11-07).
Trendlines v4 (user rules, 2026-11-07), daily chart. Down line (up line mirrored), points = confirmed Dow swing highs:
  1st point = the top: the highest swing high since the last reset (start, or the break of the previous line)
  low update = a swing low below the swing low that came before the top
  2nd point = the first swing high confirmed after that low update, below the top -> line top-2nd (no close above it between)
  later: after each new low update, the next swing high:
     within TOL x ATR of the line -> same line (outer line through the anchor, both points kept)
     clearly below the line       -> steeper: new line from the previous point to it, the old line is dropped
  a close above the line -> the line failed: deleted; the search restarts from that bar
  the daily major Dow turning the other way also deletes the line and restarts the search (no weekly-size lines)
"""
import numpy as np

TOL = 0.5


def pivots(R):
    last = {}
    for e in R['pivot_events']:
        last[e['id']] = e
    return sorted((e['idx'], e['kind'], e['price'], e['available_idx']) for e in last.values())


def build(df, R, A, tf='D1', tol=TOL, early=False, h4c=None, maxspan=None, brkbuf=0.0):
    """h4c: per daily bar, a list of (hour_end, close) of its H4 bars; given, a line that is not yet confirmed (no low update after
    its point) is deleted on an H4 close beyond it, a confirmed one only on a daily close."""
    """early=True: a point counts as soon as a pullback swing is confirmed after the top / last point (no low update needed)."""
    H, L, C = (df[z].to_numpy(float) for z in 'hlc'); n = len(df)
    P = pivots(R)
    out = []
    for up in (False, True):
        pk, ok = ('lo', 'hi') if up else ('hi', 'lo')            # pk: the line's points, ok: the opposite swings (updates)
        sg = 1 if up else -1
        ev = sorted(P, key=lambda p: (p[3], p[0]))              # in confirmation order
        better = (lambda a, b: a < b) if up else (lambda a, b: a > b)    # a more extreme than b (top side)
        worse = (lambda a, b: a > b) if up else (lambda a, b: a < b)
        st = dict(reset=0, line=None, gen=0, upd=False, last_pt=None)

        def clean(a, b):
            (i1, p1), (i2, p2) = a, b
            if i2 <= i1:
                return False
            s = (p2 - p1) / (i2 - i1)
            return all(not ((C[j] < p1 + s * (j - i1)) if up else (C[j] > p1 + s * (j - i1))) for j in range(i1 + 1, i2))

        def emit(b, why):
            ln = st['line']
            if ln:
                out.append(dict(tf=tf, side=sg, anchor=ln['anchor'], pts=list(ln['pts']), slope=ln['slope'], valid=ln['valid'], end=b,
                                why=why, gen=ln['gen'], steep=ln['steep'], top=ln['top'], conf=ln.get('conf')))

        def pull(i1, i2):
            """the pullback extreme between two points (a low update beyond it confirms the line)"""
            if i2 <= i1 + 1:
                return float(L[i1] if not up else H[i1])
            return float(L[i1 + 1:i2].min() if not up else H[i1 + 1:i2].max())

        def top_and_prior(b):
            """the top since the reset (swing highs confirmed by b), and the swing low before it"""
            hs = [p for p in P if p[1] == pk and p[0] >= st['reset'] and p[3] <= b]
            if not hs:
                return None, None
            t = min(hs, key=lambda p: p[2]) if up else max(hs, key=lambda p: p[2])
            lows = [p for p in P if p[1] == ok and p[0] < t[0] and p[3] <= b]
            return t, (lows[-1] if lows else None)

        k = 0
        trend = [x[0] for x in R['bars']]; opp = 'down' if up else 'up'
        for b in range(n):
            # the daily Dow turned against the line's direction: delete the line, restart the search from here
            if b > 0 and trend[b] == opp and trend[b - 1] != opp:
                if st['line']:
                    emit(b, 'dow')
                st.update(line=None, reset=b, upd=False)
            ln = st['line']
            if ln:
                ia_, pa_ = ln['anchor']; v = pa_ + ln['slope'] * (b - ia_)
                if ln.get('conf') is None and h4c is not None:      # provisional: an H4 close beyond the line deletes it
                    brk = any(((c < pa_ + ln['slope'] * (b - 1 + e / 24 - ia_)) if up else (c > pa_ + ln['slope'] * (b - 1 + e / 24 - ia_)))
                              for e, c in h4c[b])
                else:
                    brk = (C[b] < v - brkbuf * A[b]) if up else (C[b] > v + brkbuf * A[b])
                if brk:
                    emit(b, 'break'); st.update(line=None, reset=b, upd=False)
                elif ln.get('conf') is None and ((L[b] < ln['ref']) if not up else (H[b] > ln['ref'])):
                    ln['conf'] = b
            while k < len(ev) and ev[k][3] <= b:
                i, kind, p, av = ev[k]; k += 1
                ln = st['line']
                if kind == ok:                                   # an opposite swing: is it an update (lower low)?
                    if early:
                        ref = st['line']['pts'][-1][0] if ln else (top_and_prior(b)[0] or (None,))[0]
                        st['upd'] = ref is not None and i > ref
                        continue
                    if ln is None:
                        t, prior = top_and_prior(b)
                        if t is not None and i > t[0] and prior is not None and worse(p, prior[2]) is False and p != prior[2]:
                            st['upd'] = (p < prior[2]) if not up else (p > prior[2])
                        elif t is not None and i > t[0] and prior is not None:
                            st['upd'] = (p < prior[2]) if not up else (p > prior[2])
                    else:
                        lows = [q for q in P if q[1] == ok and q[0] < i and q[3] <= b]
                        st['upd'] = bool(lows) and ((p < lows[-1][2]) if not up else (p > lows[-1][2]))
                    continue
                # a point (swing high for a down line)
                if not st['upd']:
                    continue
                if ln is None:
                    t, _ = top_and_prior(b)
                    if t is None or i <= t[0] or not better(t[2], p):
                        continue
                    if clean((t[0], t[2]), (i, p)):
                        st['gen'] += 1
                        st['line'] = dict(anchor=(t[0], t[2]), pts=[(i, p)], slope=(p - t[2]) / (i - t[0]), valid=b, gen=st['gen'],
                                          steep=False, top=(t[0], t[2]), conf=None, ref=pull(t[0], i))
                        st['upd'] = False
                    continue
                ia, pa = ln['anchor']; v = pa + ln['slope'] * (i - ia); dist = sg * (p - v) / A[i]
                if dist < -tol:
                    continue
                if dist <= tol and maxspan is not None and i - ia > maxspan and ln['pts']:
                    dist = tol + 1                                # the 1st point is too old (weekly-size line): redraw from the previous point
                if dist <= tol:
                    s_new = (p - pa) / (i - ia)
                    s_out = min(ln['slope'], s_new) if up else max(ln['slope'], s_new)
                    if s_out != ln['slope'] and not clean(ln['anchor'], (i, p)):
                        continue
                    emit(b, 'refit'); st['line'] = dict(ln, pts=ln['pts'] + [(i, p)], slope=s_out, valid=b)
                else:
                    prev = ln['pts'][-1]
                    if clean(prev, (i, p)):
                        emit(b, 'steeper'); st['gen'] += 1
                        st['line'] = dict(anchor=prev, pts=[(i, p)], slope=(p - prev[1]) / (i - prev[0]), valid=b, gen=st['gen'],
                                          steep=True, top=ln['top'], conf=None, ref=pull(prev[0], i))
                st['upd'] = False
        emit(n - 1, 'open')
    return sorted(out, key=lambda x: x['valid'])
