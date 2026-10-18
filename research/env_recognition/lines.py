"""Causal trendline lifecycle (spec: chart_lab/TRENDLINE_RULES_REVIEW_20261018.md).

Generation (2-point / 3-point, create / revise / construction-retire) comes unchanged from
chart_lab/trendline_causal_engine.generate_lines. This module adds, bar by bar:

  Stage 1  break + 2 pivots (both classes)
    ascending line (built from lows):  CLOSE below line -> count Dow HIGH pivots formed after the
    break bar (anchor > break bar) and confirmed by now; 2nd one -> retire 'break_2pivots'.
    descending line (built from highs): mirror with Dow LOW pivots.
    A later CLOSE back on the inside resets the break and the count. Relocation is not a new pivot.
  Stage 2  impulse / correction vs CURRENT major Dow trend
    line direction == major trend -> 推進 (impulse); opposite -> 調整 (correction).
    On a major reversal: lines that were impulse are retired 'impulse_trend_reversal';
    correction lines become impulse and survive.

Decisions (pending user review):
  L1. "Subsequent pivot" = pivot anchored AFTER the break bar (a high formed before the break but
      confirmed by the breaking move does not count).
  L2. Close exactly on the line counts as inside (no break).
  L3. A geometry revise of an active line resets its break state.
  L4. Break checks start on the bar after the line becomes known (available_idx + 1).
  L5. Lines retired by this lifecycle stay retired even if the generator later revises the key.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'chart_lab'))
from trendline_causal_engine import generate_lines  # noqa: E402


def line_value(ln, i):
    a, b = ln['anchor_idx'], ln['end_idx']
    return ln['anchor_price'] + (ln['end_price'] - ln['anchor_price']) * (i - a) / (b - a)


def run(df, tf, res, gen_events=None):
    c = df.c.to_numpy(float)
    if gen_events is None:
        gen_events = generate_lines(df, tf, pivot_stream=res['pivot_events'])
    gby = {}
    for e in gen_events:
        gby.setdefault(e['available_idx'], []).append(e)
    pconf = {}
    for e in res['pivot_events']:
        if e['action'] == 'confirm':
            pconf.setdefault(e['available_idx'], []).append(e)
    piv_now = {}                       # id -> current anchor (relocations applied)
    rel = {}
    for e in res['pivot_events']:
        rel.setdefault(e['available_idx'], []).append(e)
    trend_at = [b[0] for b in res['bars']]

    active, dead, out = {}, set(), []
    history = []                       # finished lines: dict(..., created, retired, reason)

    def retire(i, key, reason):
        ln = active.pop(key)
        dead.add(key)
        ln.update(retired=i, reason=reason)
        history.append(ln)
        out.append(dict(idx=i, action='retire', key=key, reason=reason))

    for i in range(len(df)):
        for e in rel.get(i, []):
            piv_now[e['id']] = e
        # generator events
        for e in gby.get(i, []):
            k = e['key']
            if k in dead:
                continue
            if e['action'] == 'retire':
                if k in active:
                    retire(i, k, 'construction')
                continue
            geo = {x: e[x] for x in ('anchor_idx', 'end_idx', 'anchor_price', 'end_price')}
            direction = 'up' if e['kind'] == 'lo' else 'down'
            if k in active:
                active[k].update(geo, broken=None, count=set(), revised=i)
                active[k]['versions'].append((i, geo))
                out.append(dict(idx=i, action='revise', key=k))
            else:
                active[k] = dict(key=k, type=e['type'], kind=e['kind'], direction=direction, created=i,
                                 broken=None, count=set(), impulse_seen=False, versions=[(i, geo)], **geo)
                out.append(dict(idx=i, action='create', key=k))
        # stage 2: major trend reversal on this bar
        tr = trend_at[i]
        prev = trend_at[i - 1] if i else None
        if prev and tr and tr != prev:
            for k in list(active):
                if active[k]['direction'] == prev:
                    retire(i, k, 'impulse_trend_reversal')
        for ln in active.values():
            if tr and ln['direction'] == tr:
                ln['impulse_seen'] = True
        # stage 1: break / reset / pivot count
        fresh = pconf.get(i, [])
        for k in list(active):
            ln = active[k]
            if i <= ln.get('revised', ln['created']):
                continue
            v = line_value(ln, i)
            outside = c[i] < v if ln['kind'] == 'lo' else c[i] > v
            if ln['broken'] is None:
                if outside:
                    ln['broken'] = i
                    ln['count'] = set()
                    out.append(dict(idx=i, action='break', key=k))
                continue
            if not outside:
                ln['broken'] = None
                ln['count'] = set()
                out.append(dict(idx=i, action='reset', key=k))
                continue
            want = 'hi' if ln['kind'] == 'lo' else 'lo'
            for p in fresh:
                if p['kind'] == want and piv_now[p['id']]['idx'] > ln['broken']:
                    ln['count'].add(p['id'])
            if len(ln['count']) >= 2:
                retire(i, k, 'break_2pivots')
    for k, ln in active.items():
        history.append(dict(ln, retired=None, reason=None))
    return dict(lines=sorted(history, key=lambda x: x['created']), events=out)


def active_asof(result, k):
    """Lines an EA may use at the close of bar k, with their projected value and class."""
    res = []
    for ln in result['lines']:
        if ln['created'] <= k and (ln['retired'] is None or ln['retired'] > k):
            geo = [g for t, g in ln['versions'] if t <= k][-1]   # geometry known at k
            res.append(dict(ln, **geo, value=line_value(geo, k)))
    return res
