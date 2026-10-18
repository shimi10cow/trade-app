"""Causal horizontal zones from Dow events (spec: DOW_RULES_20261018.md §5).

Sources (all known only at their activation bar):
  - major REVERSAL      : broken 押し安値 / 戻り高値
  - provisional REVERSAL: broken 仮押し安値 / 仮戻り高値
  - W_TOP / W_BOTTOM    : neckline B
Geometry:
  outer edge = pivot wick (the broken level)
  inner edge = body edge nearest to that wick over the structural wave around the anchor
               (bars between the neighbouring opposite pivots known at activation, clipped to activation)
Lifecycle:
  activation = bar that broke the level (zone invisible before it in replay; drawn from anchor)
  expiry     = first LATER bar whose whole body is beyond the far edge, on the side opposite to
               where price was at activation (Z1, see README)
Merge: same physical pivot (kind + anchor) -> one zone, all source labels kept.
"""
import numpy as np


def _inner_edge(o, c, kind, anchor, lo_idx, hi_idx):
    bt = np.minimum(o, c)
    tp = np.maximum(o, c)
    seg = slice(lo_idx, hi_idx + 1)
    return float(bt[seg].min()) if kind == 'lo' else float(tp[seg].max())


def build(df, res):
    o, h, l, c = (df[z].to_numpy(float) for z in ('o', 'h', 'l', 'c'))
    n = len(df)
    # pivot anchors known at each bar (for wave bounds), from the causal pivot stream
    known = []                    # (available_idx, id, kind, idx)
    for e in res['pivot_events']:
        known.append((e['available_idx'], e['id'], e['kind'], e['idx']))

    def wave_bounds(anchor, kind, act):
        cur = {}
        for av, pid, k, idx in known:
            if av > act:
                break
            cur[pid] = (k, idx)
        opp = [idx for k, idx in cur.values() if k != kind]
        left = max([x for x in opp if x < anchor], default=max(0, anchor - 20))
        right = min([x for x in opp if x > anchor], default=act)
        return min(left + 1, anchor), max(min(right - 1, act), anchor)

    raw = []
    for e in res['all_events']:
        a = e['action']
        if a == 'REVERSAL':
            kind = 'lo' if e['frm'] == 'up' else 'hi'
            raw.append((e['idx'], kind, e['broken_anchor'], e['broken_price'], e['zone_source']))
        elif a in ('W_TOP', 'W_BOTTOM'):
            raw.append((e['idx'], 'lo' if a == 'W_TOP' else 'hi', e['b_anchor'], e['b'], e['zone_source']))

    zones = {}
    for act, kind, anchor, price, src in sorted(raw, key=lambda r: r[0]):
        key = (kind, anchor)
        if key in zones:
            z = zones[key]
            if src not in z['sources']:
                z['sources'].append(src)
            continue
        lo_i, hi_i = wave_bounds(anchor, kind, act)
        inner = _inner_edge(o, c, kind, anchor, lo_i, hi_i)
        top, bot = (inner, price) if kind == 'lo' else (price, inner)
        top, bot = max(top, bot), min(top, bot)
        side = 'below' if c[act] < bot else 'above' if c[act] > top else 'inside'
        zones[key] = dict(kind=kind, anchor=int(anchor), activation=int(act), top=top, bottom=bot,
                          sources=[src], side=side, expiry=None)

    # expiry scan (Z1): price below at activation -> ends when a later body is fully above top, and vice versa
    bt, tp = np.minimum(o, c), np.maximum(o, c)
    for z in zones.values():
        for j in range(z['activation'] + 1, n):
            if z['side'] != 'above' and bt[j] > z['top']:
                z['expiry'] = j; break
            if z['side'] != 'below' and tp[j] < z['bottom']:
                z['expiry'] = j; break
    return sorted(zones.values(), key=lambda z: z['activation'])


def active_asof(zones, k):
    """Zones an EA may use at the close of bar k (activated <= k, not yet expired at k)."""
    return [z for z in zones if z['activation'] <= k and (z['expiry'] is None or z['expiry'] > k)]
