"""Causal Dow major-trend state machine (spec: dow_frozen_v1/DOW_RULES_20261018.md §2).

Per completed bar i, in this fixed order:
  1. apply pivot confirm/relocate events with available_idx == i
  2. late confirmation: an opposite-kind pivot confirmed now whose anchor lies inside the
     last breakout leg (ref_anchor, breakout_idx] moves the protected swing (at bar i, never backdated)
  3. reversal: up & close < protected price  /  down & close > protected price
  4. breakout: up & close > reference high (snapshot before this bar's events) -> adopt the latest
     known low anchored between the reference high and now; none -> keep protected unchanged.

Decisions (documented, change only with user approval):
  D1. Protected level price is frozen when adopted (a later relocation of that pivot does not move it).
  D2. Reference for "new high" = highest confirmed high pivot anchored after the last consumed reference.
  D3. Eligible protected low on breakout = the LATEST such low (origin of the breakout leg).
  D4. On reversal, new protected = raw wick extreme of the finished trend epoch (spec exception).
  D5. Initialisation: first close beyond the last confirmed high (low) with a confirmed opposite pivot.
"""
import math
from .pivots import pivot_events


def run(df, tf, start=60, events=None):
    o, h, l, c = (df[z].to_numpy(float) for z in ('o', 'h', 'l', 'c'))
    if events is None:
        events = pivot_events(df, tf, start)
    by_bar = {}
    for e in events:
        by_bar.setdefault(e['available_idx'], []).append(e)

    piv = {}
    trend = None
    prot = None            # dict(pid, price, anchor, since)
    consumed = None        # dict(anchor, price) last broken reference
    epoch_start = None
    last_bo = None         # dict(ref_anchor, idx)
    last_hi = last_lo = None
    out = []               # state events
    bars = []              # per-bar state snapshot

    def log(i, action, **kw):
        out.append(dict(idx=i, action=action, trend=trend,
                        prot_price=prot['price'] if prot else None,
                        prot_anchor=prot['anchor'] if prot else None, **kw))

    def set_prot(i, pid, price, anchor, reason):
        nonlocal prot
        prot = dict(pid=pid, price=float(price), anchor=int(anchor), since=i)
        log(i, reason, pivot_id=pid, price=float(price), anchor=int(anchor))

    def reference():
        kind = 'hi' if trend == 'up' else 'lo'
        sgn = 1 if trend == 'up' else -1
        best = None
        for p in piv.values():
            if p['kind'] != kind or p['idx'] <= consumed['anchor']:
                continue
            if sgn * (p['price'] - consumed['price']) <= 0:
                continue
            if best is None or sgn * (p['price'] - best['price']) > 0:
                best = p
        return None if best is None else dict(id=best['id'], price=best['price'], anchor=best['idx'])

    for i in range(len(df)):
        ref = reference() if trend else None   # snapshot BEFORE this bar's events
        fresh = []
        for e in by_bar.get(i, []):
            first = e['id'] not in piv
            piv[e['id']] = dict(id=e['id'], kind=e['kind'], idx=e['idx'], price=e['price'],
                                known_at=piv.get(e['id'], {}).get('known_at', i))
            if e['action'] == 'confirm':
                fresh.append(piv[e['id']])
            if e['kind'] == 'hi':
                last_hi = e['id']
            else:
                last_lo = e['id']
            log(i, 'pivot_' + e['action'], pivot_id=e['id'], kind=e['kind'],
                price=e['price'], anchor=e['idx'], first=first)

        if trend is None:
            if last_hi is not None and last_lo is not None:
                H, L = piv[last_hi], piv[last_lo]
                if c[i] > H['price']:
                    trend = 'up'; epoch_start = L['idx']
                    consumed = dict(anchor=H['idx'], price=H['price'])
                    set_prot(i, L['id'], L['price'], L['idx'], 'init_up')
                    last_bo = dict(ref_anchor=H['idx'], idx=i)
                elif c[i] < L['price']:
                    trend = 'down'; epoch_start = H['idx']
                    consumed = dict(anchor=L['idx'], price=L['price'])
                    set_prot(i, H['id'], H['price'], H['idx'], 'init_down')
                    last_bo = dict(ref_anchor=L['idx'], idx=i)
            bars.append((trend, prot['price'] if prot else math.nan))
            continue

        up = trend == 'up'
        opp = 'lo' if up else 'hi'
        # 2. late confirmation inside last breakout leg
        for p in fresh:
            if (p['kind'] == opp and last_bo and last_bo['ref_anchor'] < p['idx'] <= last_bo['idx']
                    and p['idx'] > prot['anchor']):
                set_prot(i, p['id'], p['price'], p['idx'], 'late_protect')
        # 3. reversal
        if (up and c[i] < prot['price']) or ((not up) and c[i] > prot['price']):
            old = dict(prot)
            log(i, 'REVERSAL', frm=trend, to='down' if up else 'up',
                broken_price=old['price'], broken_anchor=old['anchor'])
            out[-1]['zone_source'] = '押し安値' if up else '戻り高値'
            seg = range(epoch_start, i + 1)
            if up:
                j = max(seg, key=lambda k: (h[k], -k)); price = h[j]
            else:
                j = min(seg, key=lambda k: (l[k], k)); price = l[j]
            trend = 'down' if up else 'up'
            epoch_start = j
            # next trend-direction reference must lie beyond the broken protected level (no reuse of
            # pivots already undercut/overshot by the reversal itself)
            consumed = dict(anchor=j, price=old['price'])
            last_bo = None
            set_prot(i, f'raw{j}', price, j, 'reversal_protect')
            bars.append((trend, prot['price']))
            continue
        # 4. breakout of reference extreme
        if ref is not None and ((up and c[i] > ref['price']) or ((not up) and c[i] < ref['price'])):
            cands = [p for p in piv.values() if p['kind'] == opp and ref['anchor'] < p['idx'] <= i
                     and p['idx'] > prot['anchor']]
            log(i, 'BREAKOUT', ref_id=ref['id'], ref_price=ref['price'], ref_anchor=ref['anchor'])
            if cands:
                p = max(cands, key=lambda q: q['idx'])
                set_prot(i, p['id'], p['price'], p['idx'], 'breakout_protect')
            consumed = dict(anchor=ref['anchor'], price=ref['price'])
            last_bo = dict(ref_anchor=ref['anchor'], idx=i)
        bars.append((trend, prot['price']))
    return dict(events=out, bars=bars, pivots=piv, pivot_events=events)


def label_counts(pivot_list):
    """HH/LH/HL/LL label for each pivot vs the previous same-kind pivot (display/count only)."""
    last = {}
    res = []
    for p in pivot_list:
        prev = last.get(p['kind'])
        if prev is None:
            lab = 'H' if p['kind'] == 'hi' else 'L'
        elif p['kind'] == 'hi':
            lab = 'HH' if p['price'] > prev['price'] else 'LH'
        else:
            lab = 'HL' if p['price'] > prev['price'] else 'LL'
        res.append(dict(p, label=lab))
        last[p['kind']] = p
    return res
