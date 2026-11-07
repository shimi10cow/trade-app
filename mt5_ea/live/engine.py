"""Common EA runner, ported from research/dow_strategy/ea_core.py (2026-10-24) to work on a Frames object.

Identical rules to the research engine (setup x trigger x stop x exit, entry at the next M15 open, stop checked before
targets, trail only tightens; optional one stop step on an H4 swing before the trail, cfg 'step'; optional level-break exits,
cfg 'd1sw' / 'h4sw', 2026-11-07). Live additions, which do not change any backtest number:
  - entry_bar=True checks the stop on the entry bar too (= research EA_ENTRY_BAR=1, what a broker-side stop does)
  - a signal on the last closed bar becomes a `pending` entry (enter at the next bar's open) instead of being dropped
  - the result also lists the positions still open at the end with their current stop (= the stop to hold at the broker)
"""
import bisect

import numpy as np
import pandas as pd

from .core import Frames


# ---------------------------------------------------------------- triggers
def trig_dow(F):
    prov = [e for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
    return {d: sorted(e['idx'] for e in prov if e['to'] == d) for d in ('up', 'down')}


def trig_all(F):
    return {'up': list(range(F.N)), 'down': list(range(F.N))}


def trig_stoch(F, n=14, k=3, dd=5, lo=20, hi=80):
    hh = pd.Series(F.h).rolling(n).max(); ll = pd.Series(F.l).rolling(n).min()
    raw = 100 * (pd.Series(F.c) - ll) / (hh - ll)
    K = raw.rolling(k).mean().to_numpy(); D = pd.Series(K).rolling(dd).mean().to_numpy()
    out = {'up': [], 'down': []}; s1 = s2 = 0
    for i in range(1, F.N):
        k_, d_, pk, pd_ = K[i], D[i], K[i - 1], D[i - 1]
        if not (np.isfinite(k_) and np.isfinite(d_)):
            continue
        if s1 == 0 and k_ < lo: s1 = 1
        elif s1 == 1 and np.isfinite(pk) and np.isfinite(pd_) and pk <= pd_ and k_ > d_: s1 = 2
        elif s1 == 2 and np.isfinite(pk) and pk <= lo and k_ > lo: s1 = 0; out['up'].append(i)
        if s2 == 0 and k_ > hi: s2 = 1
        elif s2 == 1 and np.isfinite(pk) and np.isfinite(pd_) and pk >= pd_ and k_ < d_: s2 = 2
        elif s2 == 2 and np.isfinite(pk) and pk >= hi and k_ < hi: s2 = 0; out['down'].append(i)
    return out


TRIGGERS = {'dow': trig_dow, 'all': trig_all, 'stoch': trig_stoch}


def _trigger(F, name):
    cache = F.__dict__.setdefault('_trig', {})
    if name not in cache:
        cache[name] = TRIGGERS[name](F)
    return cache[name]


# ---------------------------------------------------------------- stop references
def stop_ref(F, kind, i, s, ev=None):
    ts = F.CL15[i]; k1 = bisect.bisect_right(F.C1, ts) - 1
    want = 'lo' if s == 1 else 'hi'
    if kind == 'm15turn':
        return F.R15['prov_bars'][i][1]
    if kind == 'm15swing':
        return F.last_swing(F.P15, F.P15T, ts, want)
    if kind == 'h1swing':
        return F.last_swing(F.H1P, F.H1PT, ts, want)
    if kind == 'h1prot':
        tr, prot = F.R1['bars'][k1]
        return prot if tr == ('up' if s == 1 else 'down') else None
    if kind in ('h1ma75', 'h1ma200'):
        v = F.H1MA[int(kind[4:])][k1]
        return v if np.isfinite(v) else None
    if kind == 'ref':
        return None if ev is None else ev.get('ref')
    if kind == 'far':
        # trendline EAs (2026-11-07): the farther of the M15 turn swing and the event's line at this bar's close
        r = F.R15['prov_bars'][i][1]
        if r is None or ev is None or ev.get('line_at') is None:
            return r
        v = ev['line_at'](ts)
        return min(r, v) if s == 1 else max(r, v)
    raise ValueError(kind)


def _levels(F):
    """Cached levels for the d1sw / h4sw exits: daily swing lows / highs with the time they are known (the day after the day
    that confirmed them), the M15 bars that end a day (the bar whose next bar falls on another day by close time; the last bar
    only when the day is really over) and the M15 bars that close an H4 bar, H4 swing lows / highs (available H4 index, index, price)."""
    lv = F.__dict__.get('_lv')
    if lv is not None:
        return lv
    from env_recognition import dow_trend
    m = F.m15_all.set_index('t'); D = m.resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    RD = dow_trend.run(D[['t', 'o', 'h', 'l', 'c']], 'D1'); TD = pd.DatetimeIndex(pd.to_datetime(D.t))
    def known(kind):
        x = sorted((TD[e['available_idx']] + pd.Timedelta('1D'), e['price']) for e in RD['pivot_events'] if e['kind'] == kind)
        return [a for a, _ in x], [b for _, b in x]
    CL = pd.DatetimeIndex(F.CL15); day = CL.normalize()
    last_end = (CL[-1] + F.L15).normalize() != day[-1] if len(CL) else False
    dend = {int(i) for i in np.where(np.r_[day[1:] != day[:-1], last_end])[0]}
    C4 = pd.DatetimeIndex(F.C4); pos = CL.get_indexer(C4)
    piv4 = lambda kind: sorted(((e['available_idx'], e['idx'], e['price']) for e in F.R4['pivot_events'] if e['kind'] == kind), key=lambda x: x[0])
    lv = dict(dlo=known('lo'), dhi=known('hi'), dend=dend, h4end={int(i): k for k, i in enumerate(pos) if i >= 0}, C4=C4,
              lo4=piv4('lo'), hi4=piv4('hi'))
    F.__dict__['_lv'] = lv
    return lv


def link(F, events, trig, win=24):
    tg = _trigger(F, trig); out = {}
    for ev in events:
        d = 'up' if ev['side'] == 1 else 'down'
        i0 = F.CL15.searchsorted(ev['t']); i1 = F.CL15.searchsorted(ev['t'] + pd.Timedelta(hours=ev.get('win', win)))
        lst = tg[d]; j = bisect.bisect_left(lst, i0)
        if j < len(lst) and lst[j] < i1 and (ev.get('ok') is None or ev['ok'](lst[j])):   # 'ok': the setup's own check on its first trigger
            out.setdefault(lst[j], []).append(ev)
    return out


def run(F: Frames, events, cfg, env_ok=None, entry_bar=True):
    """Returns dict(trades=DataFrame of closed trades (R after cost), open=[positions still open], pending=[entries to place
    at the next bar's open]). cfg as in research ea_core.run."""
    ent = link(F, events, cfg.get('trig', 'dow'), cfg.get('win', 24))
    trades, pos, pending = [], [], []
    exit_kind, act, sw = cfg.get('exit', 'h1'), cfg.get('act', 1.0), cfg.get('sw', 2.0)
    N, h, l, c, o = F.N, F.h, F.l, F.c, F.o
    for i in range(N):
        keep = []
        for p in pos:
            if p['k'] > i or (p['k'] == i and not entry_bar):
                keep.append(p); continue
            s = p['side']
            if (l[i] <= p['sl']) if s == 1 else (h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = F.M15T[i]; p['why'] = 'stop'; trades.append(p); continue
            fav = s * ((h[i] if s == 1 else l[i]) - p['entry'])
            p['mfe'] = max(p['mfe'], fav / p['risk'])
            if cfg.get('tp_px') and p.get('tp_px') is not None and s * (p['tp_px'] - p['entry']) > 0 and \
                    ((h[i] >= p['tp_px']) if s == 1 else (l[i] <= p['tp_px'])):
                p['exit'] = p['tp_px']; p['exit_t'] = F.M15T[i]; p['why'] = 'target'; trades.append(p); continue
            if cfg.get('tp') and fav >= cfg['tp'] * p['risk']:
                p['exit'] = p['entry'] + s * cfg['tp'] * p['risk']; p['exit_t'] = F.M15T[i]; p['why'] = 'target'; trades.append(p); continue
            if cfg.get('tmax') and not p['trail'] and (F.M15T[i] - p['t']) >= pd.Timedelta(hours=cfg['tmax']) and \
                    max(p['mfe'], fav / p['risk']) < cfg.get('tmfe', 0.5):
                p['exit'] = c[i]; p['exit_t'] = F.M15T[i]; p['why'] = 'time'; trades.append(p); continue
            if cfg.get('lhx') or p.get('lhx'):
                # lower-high exit (USDJPY J2, 2026-11-07): once the trade has been +1R, a confirmed H1 swing high lower than the
                # previous one confirmed after the entry (sells: a higher swing low) closes it at this bar's close
                if 'lh_j' not in p:
                    p['lh_j'] = bisect.bisect_right(F.H1PT, F.CL15[p['k'] - 1]); p['lh_x'] = []
                opp, hit = ('hi' if s == 1 else 'lo'), False
                while p['lh_j'] < len(F.H1PT) and F.H1PT[p['lh_j']] <= F.CL15[i]:
                    q = F.H1P[p['lh_j']]; p['lh_j'] += 1
                    if q[1] == opp:
                        p['lh_x'].append(q[2])
                        if p['mfe'] >= 1.0 and len(p['lh_x']) >= 2 and (p['lh_x'][-1] - p['lh_x'][-2]) * s < 0:
                            hit = True
                if hit:
                    p['exit'] = c[i]; p['exit_t'] = F.M15T[i]; p['why'] = 'lh'; trades.append(p); continue
            if cfg.get('d1sw') or cfg.get('h4sw') is not None:
                # level-break exits (index H4 turn EA, 2026-11-07): close at this bar's close when
                #  d1sw: the day closes below the latest confirmed daily swing low that is above the current stop (sells mirrored)
                #  h4sw: once the trade has been +h4sw R, an H4 bar closes below the latest H4 swing low formed after the entry
                lv = _levels(F); hit = None
                if cfg.get('d1sw') and i in lv['dend'] and F.CL15[i] > p['t']:
                    T_, P_ = lv['dlo'] if s == 1 else lv['dhi']
                    j = bisect.bisect_right(T_, F.CL15[i]) - 1
                    if j >= 0 and s * (P_[j] - p['sl']) > 0 and s * (c[i] - P_[j]) < 0:
                        hit = 'd1low'
                if hit is None and cfg.get('h4sw') is not None and i in lv['h4end'] and p['mfe'] >= cfg['h4sw']:
                    k4 = lv['h4end'][i]
                    if 'k0' not in p:
                        p['k0'] = int(lv['C4'].searchsorted(p['t'], side='right'))
                    if k4 >= p['k0']:
                        piv = [x for x in (lv['lo4'] if s == 1 else lv['hi4']) if x[0] <= k4 and x[1] >= p['k0'] - 1]
                        if piv and s * (c[i] - piv[-1][2]) < 0:
                            hit = 'swlow'
                if hit:
                    p['exit'] = c[i]; p['exit_t'] = F.M15T[i]; p['why'] = hit; trades.append(p); continue
            if cfg.get('step') and not p['trail'] and not p.get('stepped'):
                # one stop step before the trail (DS, 2026-11-06): once an H4 swing on the trade's side is confirmed after the
                # entry, move the stop once to beyond it (+ step_buf x ATR(H1)); the normal trail takes over from `act`
                ts = F.M15T[i] + F.L15; want = 'lo' if s == 1 else 'hi'
                j = bisect.bisect_right(F.H4PT, ts) - 1
                while j >= 0 and F.H4P[j][1] != want:
                    j -= 1
                if j >= 0 and F.H4PT[j] > p['t']:
                    k1s = bisect.bisect_right(F.C1, F.CL15[i]) - 1
                    v = F.H4P[j][2] - s * (F.PIP + cfg.get('step_buf', 0.0) * F.A1[k1s])
                    if s * (v - p['sl']) > 0 and ((v < c[i]) if s == 1 else (v > c[i])):
                        p['sl'] = v; p['stepped'] = True
            if not p['trail'] and fav >= act * p['risk']:
                p['trail'] = True
            if p['trail']:
                xk = p.get('xk', exit_kind)       # a setup may set its own trail time frame ('xk', J2 2026-11-08)
                src = 'h4' if xk == 'h4' else 'm15' if xk == 'm15' else 'h1' if exit_kind == 'h1' or (exit_kind == 'hyb' and p['mfe'] >= sw) else 'm15'
                ts = F.M15T[i] + F.L15; want = 'lo' if s == 1 else 'hi'
                v = (F.last_swing(F.H4P, F.H4PT, ts, want) if src == 'h4' else
                     F.last_swing(F.H1P, F.H1PT, ts, want) if src == 'h1' else F.last_swing(F.P15, F.P15T, ts, want))
                if v is not None:
                    v -= s * F.PIP
                    if (v < c[i]) if s == 1 else (v > c[i]):
                        p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in ent or F.M15T[i] < F.START:
            continue
        k1 = bisect.bisect_right(F.C1, F.CL15[i]) - 1
        for ev in ent[i]:
            s = ev['side']
            same = [p for p in pos if p['side'] == s]
            if cfg.get('stack'):
                if len(same) >= cfg['stack'] or not all(p['trail'] for p in same):
                    continue
            elif cfg.get('one_per_side', True) and same:
                continue
            if cfg.get('max_side') and sum(p['side'] == s for p in pos) >= cfg['max_side']:
                continue
            if env_ok is not None and not env_ok(cfg, F.CL15[i], s):
                continue
            ref = stop_ref(F, cfg.get('stop', 'm15turn'), i, s, ev)
            if ref is None:
                continue
            if i + 1 >= N:          # signal on the last closed bar: enter at the next open (live only)
                pending.append(dict(signal_t=F.M15T[i], side=s, ref=ref, buf=cfg.get('buf', 1.0) * F.A1[k1] + cfg.get('pips', 0) * F.PIP,
                                    min_risk=10 * F.PIP, tag=ev.get('tag', ''), setup_t=ev['t'], tp_px=ev.get('tp_px')))
                continue
            entry = o[i + 1]
            sl = ref - s * (cfg.get('buf', 1.0) * F.A1[k1] + cfg.get('pips', 0) * F.PIP)
            if s * (entry - sl) <= 0:
                continue
            if s * (entry - sl) < 10 * F.PIP:
                sl = entry - s * 10 * F.PIP
            pos.append(dict(k=i + 1, t=F.M15T[i + 1], side=s, entry=entry, sl=sl, sl0=sl, risk=s * (entry - sl),
                            trail=False, mfe=0.0, tag=ev.get('tag', ''), setup_t=ev['t'], tp_px=ev.get('tp_px'),
                            **({'xk': ev['xk']} if ev.get('xk') else {}), **({'lhx': True} if ev.get('lhx') else {})))
    tr = pd.DataFrame(trades)
    if len(tr):
        tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - F.COST / tr.risk
    return dict(trades=tr, open=pos, pending=pending)
