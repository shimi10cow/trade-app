"""P: the new trend EA (新 EA / ST2 in the research notes): the original M15 stochastic EA (research/core/engine_m15.py) with seven more entry conditions,
an H1-swing trail from +1R and at most 2 positions (docs/EA_PLAN_20261102.md, RESEARCH_LOG §135-§149, 2026-11-02).

Kept from the original EA: H1 SMA20/75 regime, M15 stochastic (14,3,5) 20 -> K over D -> over 20 (sells mirrored), P1/P2 only,
H1 SMA200 slope, SMA200/480 relation, q75, MA ABCD; entry at the signal bar's M15 close; stop M15 SMA200 -/+ 10 pips (min 10).
Added (all from bars closed at the signal):
  1 daily side   : the H4 close is on the trade side of the H4 SMA1200
  2 H1 MA75 slope: H1 SMA75 - 10 bars earlier on the trade side
  3 no level bounce (off from 2026-11-03): the last 24 H1 lows (highs for sells) did not touch a level within -0.3..+0.5 ATR(H4) while the close is
                   back on the trade side. Levels: the H4 fort, the H4 exit (broken price of the last major H4 reversal),
                   a confirmed H4 swing, a confirmed D1 swing (research sx/feat.py, incl. its choice of one swing of the last 3)
  4 not too deep : H1 close - H1 SMA20 > -0.9 ATR(H1) on the trade side
  5 impulse (off from 2026-11-03): the move since the H1 regime began <= 6 ATR(H1)
  6 H4 opening   : (H4 SMA20 - SMA75) x side / ATR14(H4) < 2.5
  7 EURUSD / USDJPY only: H4 SMA75 10-bar slope x side / ATR14(H4) < 0.35
Exit: from +1R, the stop follows the last confirmed H1 swing (env_recognition pivots, 1.9 x ATR7) that is below (above) the close.
No target, no time exit. Same symbol: 2 positions at most.
Live caveat: q75 compares each signal with every earlier qualifying signal since the data start; the live window is short, so the
research history before the window is loaded from mt5_ea/live/data/q75_P_{sym}.json (as R@EURUSD does).
"""
import bisect
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from ..core import Frames
from env_recognition import dow_trend
from env_recognition.pivots import atr, pivot_events

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'research' / 'core'))
import engine_m15 as EM  # noqa: E402

COST = {'XAUUSD': 2.5e-4, 'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4}       # per trade, research price space (USDJPY / 100)
SLOPE_SYMS = {'EURUSD', 'USDJPY'}
SYMBOLS = ('XAUUSD', 'EURUSD', 'USDJPY')
OPEN_MAX, SLOPE_MAX, IMPULSE_MAX, M20_MIN = 2.5, 0.35, 6.0, -0.9
# 2026-11-03 (RESEARCH_LOG §173): conditions 3 (level bounce) and 5 (impulse) are off on all three symbols: what they removed
# was positive on all three (3-symbol total 343 -> 649 trades, t 4.92 -> 5.53, both halves positive). Still logged.
USE_BAND, USE_IMPULSE = False, False
DATA = Path(__file__).resolve().parents[1] / 'data'
M15 = pd.Timedelta(minutes=15)


def _bars(m15, rule):
    x = m15.set_index('t').resample(rule, label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna()
    x['cl'] = x.index + pd.Timedelta(rule)
    return x


def _atr_mean(b, n=14):
    pc = b.c.shift()
    return np.maximum(b.h - b.l, np.maximum((b.h - pc).abs(), (b.l - pc).abs())).rolling(n).mean()


def h4_shape(m15):
    """H4 opening and MA75 slope (research trendlab/h4f.py): (t, side) -> (opening, slope) from the last H4 bar closed by t."""
    b = _bars(m15, '4h'); a = _atr_mean(b).to_numpy(); m20 = b.c.rolling(20).mean().to_numpy(); m75 = b.c.rolling(75).mean().to_numpy()
    cl = b.cl.to_numpy()

    def f(t, s):
        k = int(np.searchsorted(cl, np.datetime64(pd.Timestamp(t)), side='right')) - 1
        if k < 10:
            return np.nan, np.nan
        return (m20[k] - m75[k]) * s / a[k], (m75[k] - m75[k - 10]) * s / a[k]
    return f


def _daily_side_slope(m15):
    """Research sx/run.py newf: H4 close vs H4 SMA1200, and the H1 SMA75 10-bar slope over an EWM ATR7."""
    h1 = _bars(m15, '1h'); pc = h1.c.shift()
    tr = np.maximum(h1.h - h1.l, np.maximum((h1.h - pc).abs(), (h1.l - pc).abs())); a1 = tr.ewm(alpha=1 / 7, adjust=False).mean()
    sl75 = ((h1.c.rolling(75).mean() - h1.c.rolling(75).mean().shift(10)) / a1).to_numpy(); C1 = h1.cl.to_numpy()
    h4 = _bars(m15, '4h'); side_d = np.sign(h4.c - h4.c.rolling(1200).mean()).to_numpy(); C4 = h4.cl.to_numpy()

    def f(t, s):
        t = np.datetime64(pd.Timestamp(t)); k1 = np.searchsorted(C1, t, side='right') - 1; k4 = np.searchsorted(C4, t, side='right') - 1
        if k1 < 0 or k4 < 0 or not np.isfinite(sl75[k1]) or not np.isfinite(side_d[k4]):
            return False
        return side_d[k4] == s and sl75[k1] * s > 0
    return f


def _levels(F: Frames):
    """Research sx/feat.py: level-bounce flag ('帯') and the H1 MA20 distance at te = signal bar close."""
    h4 = F.h4; C4 = pd.Series(pd.to_datetime(h4.t) + pd.Timedelta('4h')); A4 = atr(h4); b4 = F.R4['bars']
    d1 = h4.set_index('t').resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    d1 = d1[d1.t.dt.dayofweek < 5].reset_index(drop=True)
    RD = dow_trend.run(d1, 'D1'); CD = pd.Series(pd.to_datetime(d1.t) + pd.Timedelta('1D'))
    h1 = F.h1; C1 = pd.Series(pd.to_datetime(h1.t) + pd.Timedelta('1h')); A1 = atr(h1)
    c1, hi1, lo1 = h1.c.to_numpy(), h1.h.to_numpy(), h1.l.to_numpy(); m20 = h1.c.rolling(20).mean().to_numpy()
    rev = [x for x in F.R4['events'] if x.get('machine') == 'major' and x['action'] == 'REVERSAL']; revk = [x['idx'] for x in rev]
    sw = {k: sorted((x['available_idx'], x['price']) for x in F.R4['pivot_events'] if x['action'] == 'confirm' and x['kind'] == k) for k in ('hi', 'lo')}
    swk = {k: [a for a, _ in v] for k, v in sw.items()}
    swd = {k: sorted((x['available_idx'], x['price']) for x in RD['pivot_events'] if x['action'] == 'confirm' and x['kind'] == k) for k in ('hi', 'lo')}
    swdk = {k: [a for a, _ in v] for k, v in swd.items()}

    def f(te, s):
        want = 'up' if s == 1 else 'down'
        k4 = int(C4.searchsorted(te, side='right')) - 1; kd = int(CD.searchsorted(te, side='right')) - 1; k1 = int(C1.searchsorted(te, side='right')) - 1
        if k4 < 0 or kd < 0 or k1 < 23:
            return True, np.nan
        a = A4[k4]; lv = {}
        if b4[k4][0] == want and b4[k4][1] is not None:
            lv['fort'] = b4[k4][1]
        j = bisect.bisect_right(revk, k4) - 1
        if j >= 0 and rev[j]['to'] == want:
            lv['exit'] = rev[j]['broken_price']
        kk = 'lo' if s == 1 else 'hi'; q = bisect.bisect_right(swk[kk], k4)
        for _, p in sw[kk][max(0, q - 3):q]:
            lv.setdefault('h4sw', p)
        q = bisect.bisect_right(swdk[kk], kd)
        for _, p in swd[kk][max(0, q - 3):q]:
            lv.setdefault('d1sw', p)
        lo24 = lo1[k1 - 23:k1 + 1].min(); hi24 = hi1[k1 - 23:k1 + 1].max()
        hit = any(((L - 0.3 * a <= lo24 <= L + 0.5 * a and c1[k1] > L) if s == 1 else (L + 0.3 * a >= hi24 >= L - 0.5 * a and c1[k1] < L)) for L in lv.values())
        return hit, (c1[k1] - m20[k1]) * s / A1[k1]
    return f


def _impulse(m, h1):
    """Research sx/exits.py: largest move since the H1 regime began (base -> extreme) in engine H1 ATR, at the signal bar.
    NaN (= not allowed) when the regime began 4 M15 bars ago or less."""
    T = m.time.to_numpy(); H = m.high.to_numpy(); L = m.low.to_numpy()
    Ch = h1.avail_time.to_numpy(); a1 = h1.atr.to_numpy(); rs = h1.regside.to_numpy()

    def f(t, s):
        t = np.datetime64(pd.Timestamp(t)); i = int(np.searchsorted(T, t)); k1 = int(np.searchsorted(Ch, t, side='right')) - 1
        if k1 < 0:
            return np.nan
        reg = np.flatnonzero(rs[:k1 + 1] != s); rstart = Ch[reg[-1]] if len(reg) else Ch[0]
        i0 = int(np.searchsorted(T, rstart))
        if i - i0 <= 4:
            return np.nan
        seg = slice(i0, i + 1); hh = np.argmax(H[seg]) if s == 1 else np.argmin(L[seg]); jh = i0 + hh; ext = H[jh] if s == 1 else L[jh]
        base = (L[i0:jh + 1].min() if s == 1 else H[i0:jh + 1].max()) if jh > i0 else (L[i0] if s == 1 else H[i0])
        return (ext - base) * s / a1[k1]
    return f


def _h1_pivots(h1, m15_times):
    """Confirmed H1 swings (env_recognition, 1.9 x ATR7) as the engine's trail pivots (kind L/H, price, confirm_time).
    The engine stores a pivot on the M15 bar whose time equals confirm_time and uses it from the next bar. An H1 bar that
    closes into a gap (weekend, holiday) has no M15 bar at its close time, so its pivot is keyed to the last M15 bar before
    it: it is then used from the first bar after the gap, as in the research trail (pivots confirmed before the bar)."""
    ev = pivot_events(h1.rename(columns=dict(open='o', high='h', low='l', close='c'))[['o', 'h', 'l', 'c']].reset_index(drop=True))
    Ch = h1.avail_time.reset_index(drop=True); T = np.asarray(m15_times, dtype='datetime64[ns]')
    rows = []
    for e in ev:
        if e['action'] != 'confirm':
            continue
        c = np.datetime64(Ch[e['available_idx']]); k = int(np.searchsorted(T, c, side='right')) - 1
        if k < 0:
            continue
        rows.append(dict(kind='L' if e['kind'] == 'lo' else 'H', price=e['price'], confirm_time=pd.Timestamp(T[k])))
    return pd.DataFrame(rows).sort_values('confirm_time').reset_index(drop=True)


_SEED = {}


def q75_seed(sym, before):
    if sym not in _SEED:
        f = DATA / f'q75_P_{sym}.json'
        _SEED[sym] = json.loads(f.read_text())['points'] if f.exists() else []
    b = str(pd.Timestamp(before)); out = {1: [], -1: []}
    for t, sd, v in _SEED[sym]:
        if t < b:
            out[int(sd)].append(v)
    return out


def config(F: Frames, sym, m15, log=None):
    """Engine config with the seven extra entry conditions (log: optional dict collecting each check, for the parity test)."""
    d = m15.rename(columns=dict(t='time', o='open', h='high', l='low', c='close'))[['time', 'open', 'high', 'low', 'close']].copy()
    old = EM.load_m15; EM.load_m15 = lambda pair: d.copy()
    try:
        m, h1, _, _, _ = EM.build_features('EURUSD')
    finally:
        EM.load_m15 = old
    side_slope = _daily_side_slope(m15); lev = _levels(F); imp = _impulse(m, h1); shape = h4_shape(m15)

    def extra(t, s):
        if not side_slope(t, s):
            return False
        hit, m20d = lev(pd.Timestamp(t) + M15, s)
        ip = imp(t, s); op, sl4 = shape(t, s)
        ok = (not (USE_BAND and hit)) and m20d > M20_MIN and (not USE_IMPULSE or ip <= IMPULSE_MAX) and op < OPEN_MAX \
            and (sym not in SLOPE_SYMS or sl4 < SLOPE_MAX)
        if log is not None:
            log[(pd.Timestamp(t), s)] = dict(band=hit, m20d=m20d, imp=ip, op=op, sl4=sl4, ok=ok)
        return bool(ok)
    return EM.Config(extra_filter=extra, max_positions=2, use_delayed_zz=False, trail_start_R=1.0, trail_close_check=True,
                     trail_pivots=_h1_pivots(h1, m.time.to_numpy()))


def run(F: Frames, sym, env=None, m15=None, seed=True, log=None):
    """Returns dict(trades, open, pending) like rt.run (t = signal bar time, entry at that bar's close)."""
    src = F.m15_all if m15 is None else m15
    cfg = config(F, sym, src, log)
    if seed:
        cfg.q75_seed = q75_seed(sym, src.t.iat[0])
    d = src.rename(columns=dict(t='time', o='open', h='high', l='low', c='close'))[['time', 'open', 'high', 'low', 'close']].copy()
    d['time'] = pd.to_datetime(d.time); d = d.sort_values('time').drop_duplicates('time').reset_index(drop=True)
    old = EM.load_m15; EM.load_m15 = lambda pair: d.copy()
    try:
        tr = EM.run_pair('EURUSD', cfg)          # pair name only sets the pip size (1e-4 in the research price space)
    finally:
        EM.load_m15 = old
    if not len(tr):
        return dict(trades=pd.DataFrame(), open=[], pending=[])
    tr = tr.rename(columns=dict(time='t', ExitTime='exit_t', initial_sl='sl0'))
    tr['R'] = tr.R - COST.get(sym, 1.2e-4) / tr.risk
    last_i = len(d) - 1
    is_open = tr.get('open_end', pd.Series(False, index=tr.index)).fillna(False).astype(bool)
    closed = tr[~is_open & (pd.to_datetime(tr.t) >= F.START)].reset_index(drop=True)
    op = tr[is_open & (pd.to_datetime(tr.t) >= F.START)]
    opened = [dict(r) for _, r in op[op.entry_i < last_i].iterrows()]
    pending = [dict(r, signal_t=r['t']) for _, r in op[op.entry_i == last_i].iterrows()]
    return dict(trades=closed, open=opened + pending, pending=pending)
