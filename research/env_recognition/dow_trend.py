"""Causal Dow trend state machines (spec: dow_frozen_v1/DOW_RULES_20261018.md §2-§4).

Two machines share the same rules and run side by side on the same pivot stream:
  major       (主要トレンド) — changes only when the protected swing is closed through.
  provisional (仮トレンド)   — same rules, PLUS a pattern start (§3): in a non-up state, with
               confirmed H1,L1,H2,L2 (L2>L1) and H1 already closed above, a CLOSE above H2 starts
               provisional up with protected low L2 (mirror for down). Lets the inner direction
               flip while the major protected swing has not moved.
W top/bottom (§4) is detected against the major trend.

Per completed bar i, each machine runs in this fixed order:
  1. (pivots with available_idx == i are already applied)
  2. late confirmation: opposite pivot confirmed now, anchored inside the last breakout leg
     (ref_anchor, breakout_idx], moves the protected swing (at bar i, never backdated)
  3. reversal: up & close < protected / down & close > protected
  4. breakout: close beyond the reference extreme (snapshot before this bar's events) ->
     protected = latest known opposite pivot anchored between reference and now
  5. provisional only: pattern start

Decisions (D4 confirmed by user 2026-10-18; others pending review):
  D1. Protected price is frozen when adopted (a later relocation of that pivot does not move it).
  D2. Reference "high to beat" = highest confirmed high anchored after the last consumed reference.
  D3. Protected on breakout = LATEST eligible opposite pivot (origin of the breakout leg).
  D4. On reversal, new protected = latest confirmed opposite swing after the broken protected
      (origin of the breaking move); raw wick extreme only as fallback.
  D5. After a reversal the next reference must lie beyond the broken protected level.
  D6. Initialisation: first close beyond the last confirmed high (low) with a confirmed opposite pivot.
"""
from .pivots import pivot_events


class DowMachine:
    def __init__(self, name, h, l, c, piv, provisional=False):
        self.name, self.h, self.l, self.c, self.piv = name, h, l, c, piv
        self.provisional = provisional
        self.trend = None
        self.prot = None
        self.consumed = None
        self.last_bo = None
        self.ref = None
        self.epoch = 0          # increments on every trend change
        self.out = []
        self.bars = []

    # ------------------------------------------------------------------ helpers
    def log(self, i, action, **kw):
        p = self.prot
        self.out.append(dict(idx=i, machine=self.name, action=action, trend=self.trend,
                             prot_price=p['price'] if p else None,
                             prot_anchor=p['anchor'] if p else None, **kw))

    def set_prot(self, i, pid, price, anchor, reason):
        self.prot = dict(pid=pid, price=float(price), anchor=int(anchor), since=i)
        self.log(i, reason, pivot_id=pid, price=float(price), anchor=int(anchor))

    def reference(self):
        if not self.trend:
            return None
        # cache: the answer only depends on the pivot set (version bumped by run()), the trend and the consumed swing
        pver = getattr(self, 'pver', None)
        if pver is not None:
            key = (pver, self.trend, self.consumed['anchor'], self.consumed['price'])
            if key == getattr(self, '_ref_key', None):
                return None if self._ref_val is None else dict(self._ref_val)
            val = self._reference()
            self._ref_key, self._ref_val = key, val
            return None if val is None else dict(val)
        return self._reference()

    def _reference(self):
        kind = 'hi' if self.trend == 'up' else 'lo'
        sgn = 1 if self.trend == 'up' else -1
        best = None
        for p in self.piv.values():
            if p['kind'] != kind or p['idx'] <= self.consumed['anchor']:
                continue
            if sgn * (p['price'] - self.consumed['price']) <= 0:
                continue
            if best is None or sgn * (p['price'] - best['price']) > 0:
                best = p
        return None if best is None else dict(id=best['id'], price=best['price'], anchor=best['idx'])

    def start(self, i, trend, prot_pivot, consumed_pivot, reason):
        self.trend = trend
        self.epoch += 1
        self.consumed = dict(anchor=consumed_pivot['idx'], price=consumed_pivot['price'])
        self.set_prot(i, prot_pivot['id'], prot_pivot['price'], prot_pivot['idx'], reason)
        self.last_bo = dict(ref_anchor=consumed_pivot['idx'], idx=i)

    # ------------------------------------------------------------------ per bar
    def snapshot_ref(self):
        self.ref = self.reference()

    def step(self, i, fresh, last_hi, last_lo, seq):
        c, h, l, piv = self.c, self.h, self.l, self.piv
        if self.trend is None:
            if last_hi is not None and last_lo is not None:
                H, L = piv[last_hi], piv[last_lo]
                if c[i] > H['price']:
                    self.start(i, 'up', L, H, 'init_up')
                elif c[i] < L['price']:
                    self.start(i, 'down', H, L, 'init_down')
            if self.trend is None and self.provisional:
                self.pattern(i, seq)
            self.bars.append((self.trend, self.prot['price'] if self.prot else None))
            return
        up = self.trend == 'up'
        opp = 'lo' if up else 'hi'
        # 2. late confirmation
        lb = self.last_bo
        for p in fresh:
            if (p['kind'] == opp and lb and lb['ref_anchor'] < p['idx'] <= lb['idx']
                    and p['idx'] > self.prot['anchor']):
                self.set_prot(i, p['id'], p['price'], p['idx'], 'late_protect')
        # 3. reversal
        if (up and c[i] < self.prot['price']) or ((not up) and c[i] > self.prot['price']):
            self.reverse(i)
            self.bars.append((self.trend, self.prot['price']))
            return
        # 4. breakout
        ref = self.ref
        if ref is not None and ((up and c[i] > ref['price']) or ((not up) and c[i] < ref['price'])):
            cands = [p for p in piv.values() if p['kind'] == opp and ref['anchor'] < p['idx'] <= i
                     and p['idx'] > self.prot['anchor']]
            self.log(i, 'BREAKOUT', ref_id=ref['id'], ref_price=ref['price'], ref_anchor=ref['anchor'])
            if cands:
                p = max(cands, key=lambda q: q['idx'])
                self.set_prot(i, p['id'], p['price'], p['idx'], 'breakout_protect')
            self.consumed = dict(anchor=ref['anchor'], price=ref['price'])
            self.last_bo = dict(ref_anchor=ref['anchor'], idx=i)
        # 5. provisional pattern start
        elif self.provisional:
            self.pattern(i, seq)
        self.bars.append((self.trend, self.prot['price']))

    def reverse(self, i):
        h, l, piv = self.h, self.l, self.piv
        up = self.trend == 'up'
        old = dict(self.prot)
        self.log(i, 'REVERSAL', frm=self.trend, to='down' if up else 'up',
                 broken_price=old['price'], broken_anchor=old['anchor'],
                 zone_source=('仮' if self.provisional else '') + ('押し安値' if up else '戻り高値'))
        nk = 'hi' if up else 'lo'
        cands = [p for p in piv.values() if p['kind'] == nk and old['anchor'] < p['idx'] < i]
        if cands:
            p = max(cands, key=lambda q: q['idx'])
            j, price, pid, why = p['idx'], p['price'], p['id'], 'reversal_protect'
        else:
            seg = range(old['anchor'] + 1, i + 1)
            j = max(seg, key=lambda k: (h[k], -k)) if up else min(seg, key=lambda k: (l[k], k))
            price = h[j] if up else l[j]
            pid, why = f'raw{j}', 'reversal_protect_raw'
        self.trend = 'down' if up else 'up'
        self.epoch += 1
        self.consumed = dict(anchor=j, price=old['price'])
        self.last_bo = None
        self.set_prot(i, pid, price, j, why)

    def pattern(self, i, seq):
        """§3 start: last four confirmed pivots H1,L1,H2,L2 (up) or L1,H1,L2,H2 (down)."""
        if len(seq) < 4:
            return
        a, b, x, y = (self.piv[k] for k in seq[-4:])
        c = self.c
        # provisional up: H1 L1 H2 L2, L2 > L1, H1 already closed above, close > H2
        if (self.trend != 'up' and a['kind'] == 'hi' and y['kind'] == 'lo' and y['price'] > b['price']
                and c[a['idx'] + 1:i].max(initial=-1e18) > a['price'] and c[i] > x['price']):
            self.log(i, 'PROV_START', to='up', h1=a['price'], l1=b['price'], h2=x['price'], l2=y['price'])
            self.start(i, 'up', y, x, 'prov_protect')
        # provisional down: L1 H1 L2 H2, H2 < H1, L1 already closed below, close < L2
        elif (self.trend != 'down' and a['kind'] == 'lo' and y['kind'] == 'hi' and y['price'] < b['price']
                and c[a['idx'] + 1:i].min(initial=1e18) < a['price'] and c[i] < x['price']):
            self.log(i, 'PROV_START', to='down', l1=a['price'], h1=b['price'], l2=x['price'], h2=y['price'])
            self.start(i, 'down', y, x, 'prov_protect')


class WDetector:
    """§4: in major up, confirmed A(hi) B(lo) C(hi), no close above A between A and C,
    then CLOSE below B -> W top (zone at B). Mirror in major down. Max 2 per major epoch."""

    def __init__(self, c, piv):
        self.c, self.piv = c, piv
        self.used = set()
        self.count = {}
        self.out = []

    def step(self, i, major, seq):
        if major.trend is None or len(seq) < 3:
            return
        up = major.trend == 'up'
        if self.count.get(major.epoch, 0) >= 2:
            return
        # latest A,B,C of the right kinds among the last 4 confirmed pivots
        for k in range(len(seq) - 3, max(len(seq) - 5, -1), -1):
            a, b, cc = (self.piv[x] for x in seq[k:k + 3])
            if (a['kind'], b['kind'], cc['kind']) == (('hi', 'lo', 'hi') if up else ('lo', 'hi', 'lo')):
                break
        else:
            return
        key = (a['id'], b['id'], cc['id'])
        if key in self.used:
            return
        c = self.c
        seg = c[a['idx'] + 1:cc['idx'] + 1]
        if up and (seg > a['price']).any() or (not up) and (seg < a['price']).any():
            return
        # neckline must not have been closed through already before this bar
        after = c[b['idx'] + 1:i]
        if up and (after < b['price']).any() or (not up) and (after > b['price']).any():
            self.used.add(key)
            return
        if (up and c[i] < b['price']) or ((not up) and c[i] > b['price']):
            self.used.add(key)
            self.count[major.epoch] = self.count.get(major.epoch, 0) + 1
            self.out.append(dict(idx=i, machine='W', action='W_TOP' if up else 'W_BOTTOM',
                                 trend=major.trend, a=a['price'], a_anchor=a['idx'], b=b['price'],
                                 b_anchor=b['idx'], c=cc['price'], c_anchor=cc['idx'],
                                 zone_source='ダブルトップB' if up else 'ダブルボトムB',
                                 same_bar_major_reversal=False))


def run(df, tf, start=60, events=None):
    h, l, c = (df[z].to_numpy(float) for z in ('h', 'l', 'c'))
    if events is None:
        events = pivot_events(df, tf, start)
    by_bar = {}
    for e in events:
        by_bar.setdefault(e['available_idx'], []).append(e)

    piv = {}
    seq = []                 # confirmed pivot ids in anchor order (relocation keeps the id)
    major = DowMachine('major', h, l, c, piv)
    prov = DowMachine('prov', h, l, c, piv, provisional=True)
    major.pver = prov.pver = 0
    wdet = WDetector(c, piv)
    pivlog = []
    last_hi = last_lo = None
    for i in range(len(df)):
        major.snapshot_ref(); prov.snapshot_ref()
        fresh = []
        if i in by_bar:
            major.pver += 1; prov.pver += 1
        for e in by_bar.get(i, []):
            first = e['id'] not in piv
            piv[e['id']] = dict(id=e['id'], kind=e['kind'], idx=e['idx'], price=e['price'],
                                known_at=piv.get(e['id'], {}).get('known_at', i))
            if first:
                seq.append(e['id'])
            if e['action'] == 'confirm':
                fresh.append(piv[e['id']])
            if e['kind'] == 'hi':
                last_hi = e['id']
            else:
                last_lo = e['id']
            pivlog.append(dict(idx=i, machine='pivot', action='pivot_' + e['action'], pivot_id=e['id'],
                               kind=e['kind'], price=e['price'], anchor=e['idx'], first=first))
        major_epoch_before = major.epoch
        major.step(i, fresh, last_hi, last_lo, seq)
        prov.step(i, fresh, last_hi, last_lo, seq)
        n_w = len(wdet.out)
        # W is judged inside the epoch that existed before this bar (same-bar reversal counts too)
        wdet.step(i, _EpochView(major, major_epoch_before), seq)
        if len(wdet.out) > n_w and major.epoch != major_epoch_before:
            wdet.out[-1]['same_bar_major_reversal'] = True
    events_all = sorted(pivlog + major.out + prov.out + wdet.out, key=lambda e: e['idx'])
    return dict(events=[e for e in events_all if e['machine'] in ('pivot', 'major')],
                prov_events=prov.out, w_events=wdet.out, all_events=events_all,
                bars=major.bars, prov_bars=prov.bars, pivots=piv, pivot_events=events)


class _EpochView:
    """Major state as it was at the start of the bar (trend/epoch before any same-bar reversal)."""

    def __init__(self, major, epoch_before):
        self.epoch = epoch_before
        rev = [e for e in major.out[-3:] if e['action'] == 'REVERSAL']
        self.trend = rev[-1]['frm'] if major.epoch != epoch_before and rev else major.trend


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
