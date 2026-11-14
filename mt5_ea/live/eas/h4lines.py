"""H4 horizontal lines (A / B) and the T2@EURUSD "line just ahead" skip (2026-11-14, docs/OPEN_ITEMS.md D17).

Every major H4 Dow reversal (F.R4 events, machine 'major', action 'REVERSAL') makes two lines:
  A = the broken price (the protected low / high whose break turned the H4 Dow)
  B = the extreme of the trend that just ended (lowest low / highest high between the previous reversal and this one)
A line is born at the close of the reversal bar. After a turn up both lines are below the price and a line dies at the
first H4 close >= 1 ATR14(H4) below it (after a turn down: above it). Lines older than 180 days are not used.

T2 skip: at an entry, if an alive line lies ahead of the entry (above for buys, below for sells) within 1R
(R = entry - initial stop), the entry is skipped. The skip is done in the engine's sl_fn, so a skipped signal does not
take one of T2's 2 position slots (research: 70 skipped, 7 new entries, 2005-2026 server time).
"""
import numpy as np
import pandas as pd

from ..core import Frames

CUTOVER = pd.Timestamp('2026-11-15 00:00')   # live: entries from here; the backtest before keeps the old T2
MAX_R = 1.0
DAYS = 180
NEVER = pd.Timestamp('2100-01-01')


def _atr14(b):
    pc = b.c.shift()
    return pd.concat([b.h - b.l, (b.h - pc).abs(), (b.l - pc).abs()], axis=1).max(axis=1).rolling(14).mean().to_numpy()


def lines(F: Frames):
    """DataFrame(kind 'A'/'B', born, p, dead): every A / B line of F's H4 bars (born / dead = H4 close times)."""
    h4 = F.h4.reset_index(drop=True); a = _atr14(h4); C4 = list(F.C4)
    H, L, C = h4.h.to_numpy(), h4.l.to_numpy(), h4.c.to_numpy()
    out = []; prev = 0
    for e in F.R4['events']:
        if e.get('machine') != 'major' or e['action'] != 'REVERSAL':
            continue
        k = e['idx']; up = e['to'] == 'up'; ds = -1 if up else 1
        for kind, p in (('A', e['broken_price']), ('B', L[prev:k + 1].min() if up else H[prev:k + 1].max())):
            hit = np.nonzero(np.isfinite(a[k + 1:]) & (ds * (C[k + 1:] - p) >= a[k + 1:]))[0]
            out.append((kind, C4[k], float(p), C4[k + 1 + hit[0]] if len(hit) else NEVER))
        prev = k
    return pd.DataFrame(out, columns=['kind', 'born', 'p', 'dead'])


def near_skip(F: Frames, cutover=None, max_r=MAX_R, days=DAYS):
    """sl_fn for the M15 engine: None (skip) when an alive H4 line is ahead within max_r x risk; else the stop unchanged.
    cutover: None = CUTOVER, False = the whole history (research), or a Timestamp."""
    cut = CUTOVER if cutover is None else (None if cutover is False else pd.Timestamp(cutover))
    LN = lines(F)
    born, p, dead = LN.born.to_numpy(dtype='datetime64[ns]'), LN.p.to_numpy(), LN.dead.to_numpy(dtype='datetime64[ns]')
    span = np.timedelta64(days, 'D')

    def fn(t, side, entry, sl):
        t = pd.Timestamp(t)
        if cut is not None and t < cut:
            return sl
        tt = np.datetime64(t)
        alive = (born <= tt) & (dead > tt) & (born > tt - span)
        ahead = (p[alive] - entry) * side
        ahead = ahead[ahead > 0]
        risk = abs(entry - sl)
        if len(ahead) and risk > 0 and ahead.min() / risk <= max_r:
            return None
        return sl
    return fn
