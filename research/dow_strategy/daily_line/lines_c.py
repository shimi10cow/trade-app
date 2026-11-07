"""Daily trendlines, version C (user, 2026-11-07): points placed provisionally on H4 swings, confirmed by the low update.
Down line (up line mirrored). Time runs on H4 bars.
  top        = the highest high since the reset (start, a confirmed line's break, or the daily Dow turning up)
  provisional 2nd point = an H4 swing high confirmed after an H4 swing low that came after the top, below the top, with no H4 close
               above the straight line top -> point between them
  provisional line: an H4 close above it deletes it; the top stays, the next H4 swing high to the right gives a new one
  confirmed  : price trades below the pullback low between the two points (the low update)
  confirmed line: a daily close above it deletes it and restarts the search
  later points (after a low update since the last point): an H4 swing high within TOL x ATR(D1) of the line keeps the line
               (outer line through the anchor); clearly below -> steeper line from the previous point (provisional again),
               the old line is dropped
"""
import bisect
import numpy as np
import pandas as pd

TOL = 0.5


def pivots(R):
    last = {}
    for e in R['pivot_events']:
        last[e['id']] = e
    return sorted((e['idx'], e['kind'], e['price'], e['available_idx']) for e in last.values())


def build(h4, R4, d1, RD, AD, tol=TOL, depth=1.0, bounce=0.5, dconf=False):
    """depth: the pullback from the top to the low before the 2nd point, in ATR(D1); bounce: the rally from that low to the 2nd point"""
    H, L, C = (h4[z].to_numpy(float) for z in 'hlc'); n = len(h4)
    t4 = pd.to_datetime(h4.t).to_numpy(); td = pd.to_datetime(d1.t).to_numpy()
    day = np.searchsorted(td, t4, side='right') - 1                     # daily bar of each H4 bar
    DC = d1.c.to_numpy(float); dtrend = [b[0] for b in RD['bars']]
    P = pivots(R4); DP = pivots(RD)
    out = []
    for up in (False, True):
        pk, ok = ('lo', 'hi') if up else ('hi', 'lo'); sg = 1 if up else -1
        ev = sorted(P, key=lambda p: (p[3], p[0]))
        X = L if up else H
        st = dict(reset=0, line=None, gen=0, opp_after=None, upd=False)

        def lv(ln, x):
            return ln['anchor'][1] + ln['slope'] * (x - ln['anchor'][0])

        def clean(a, b):
            (i1, p1), (i2, p2) = a, b
            if i2 <= i1:
                return False
            s = (p2 - p1) / (i2 - i1)
            return all(not ((C[j] < p1 + s * (j - i1)) if up else (C[j] > p1 + s * (j - i1))) for j in range(i1 + 1, i2))

        def pull(i1, i2):
            return float(H[i1 + 1:i2].max()) if up else float(L[i1 + 1:i2].min())

        def emit(b, why):
            ln = st['line']
            if ln:
                out.append(dict(side=sg, anchor=ln['anchor'], pts=list(ln['pts']), slope=ln['slope'], valid=ln['valid'], end=b, why=why,
                                gen=ln['gen'], steep=ln['steep'], conf=ln['conf'], hist=list(ln['hist'])))

        def top(b):
            j0 = st['reset']
            if b <= j0:
                return None
            seg = X[j0:b + 1]; j = j0 + (int(np.argmin(seg)) if up else int(np.argmax(seg)))
            return (j, float(X[j]))

        k = 0; last_day = -1; opp = 'down' if up else 'up'
        for b in range(n):
            dd = day[b]
            if dd != last_day and dd >= 0:                               # a new day: the daily Dow / the confirmed line's daily close
                if last_day >= 0:
                    pd_ = last_day
                    ln = st['line']
                    if ln and ln['conf'] is not None:
                        # the previous day's close against the line value at the end of that day
                        jb = b - 1
                        if (DC[pd_] < lv(ln, jb)) if up else (DC[pd_] > lv(ln, jb)):
                            emit(jb, 'break'); st.update(line=None, reset=b, upd=False, opp_after=None)
                    if dtrend[dd] == opp and dtrend[pd_] != opp:
                        if st['line']:
                            emit(b, 'dow')
                        st.update(line=None, reset=b, upd=False, opp_after=None)
                last_day = dd
            ln = st['line']
            if ln and ln['conf'] is None:                                # provisional: an H4 close beyond deletes it, the top stays
                if (C[b] < lv(ln, b)) if up else (C[b] > lv(ln, b)):
                    ln['hist'].append(('仮ラインが割れた', b))
                    emit(b, 'prov_break'); st['line'] = None; st['opp_after'] = None
                    ln = None
                elif (L[b] < ln['ref']) if not up else (H[b] > ln['ref']):
                    ln['conf'] = b
            while k < len(ev) and ev[k][3] <= b:
                i, kind, p, _ = ev[k]; k += 1
                ln = st['line']
                if kind == ok:
                    t = top(b)
                    if ln is None:
                        if t is not None and i > t[0]:
                            st['opp_after'] = i                          # a pullback swing after the top
                    else:
                        last = ln['pts'][-1][0]
                        st['upd'] = i > last and ((p < ln['ref2']) if not up else (p > ln['ref2']))
                    continue
                if ln is None:
                    t = top(b)
                    if t is None or st['opp_after'] is None or i <= st['opp_after'] or not ((p > t[1]) if up else (p < t[1])):
                        continue
                    lo_ = pull(t[0], i); a_ = AD[day[i]]
                    if not (sg * (t[1] - lo_) * -1 >= depth * a_ if up else (t[1] - lo_) >= depth * a_):
                        continue                                  # the pullback is not daily-sized
                    if not ((lo_ - p) >= bounce * a_ if up else (p - lo_) >= bounce * a_):
                        continue                                  # the bounce to the point is too small
                    if clean(t, (i, p)):
                        st['gen'] += 1
                        ref = pull(t[0], i)
                        if dconf:                         # confirmation = below the daily swing low before the top
                            dl = [q for q in DP if q[1] == ok and q[0] < day[t[0]] and q[3] <= day[b]]
                            if dl:
                                ref = min(ref, dl[-1][2]) if not up else max(ref, dl[-1][2])
                        st['line'] = dict(anchor=t, pts=[(i, p)], slope=(p - t[1]) / (i - t[0]), valid=b, gen=st['gen'], steep=False,
                                          conf=None, ref=ref, ref2=pull(t[0], i), hist=[])
                        st['upd'] = False
                    continue
                if ln['conf'] is None or not st['upd']:
                    continue
                a = AD[day[i]] if day[i] >= 0 else np.nan
                dist = sg * (p - lv(ln, i)) / a
                if dist < -tol:
                    continue
                if dist <= tol:
                    s_new = (p - ln['anchor'][1]) / (i - ln['anchor'][0])
                    s_out = min(ln['slope'], s_new) if up else max(ln['slope'], s_new)
                    if s_out != ln['slope'] and not clean(ln['anchor'], (i, p)):
                        continue
                    ln['pts'].append((i, p)); ln['slope'] = s_out; ln['ref2'] = pull(ln['pts'][-2][0], i)
                else:
                    prev = ln['pts'][-1]
                    if clean(prev, (i, p)):
                        emit(b, 'steeper'); st['gen'] += 1
                        st['line'] = dict(anchor=prev, pts=[(i, p)], slope=(p - prev[1]) / (i - prev[0]), valid=b, gen=st['gen'],
                                          steep=True, conf=None, ref=pull(prev[0], i), ref2=pull(prev[0], i), hist=[])
                st['upd'] = False
        emit(n - 1, 'open')
    return sorted(out, key=lambda x: x['valid'])
