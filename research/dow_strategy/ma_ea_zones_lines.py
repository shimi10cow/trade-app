"""Existing MA+Stochastic EA + Dow filter (H1 & H4 major trend agree) + horizontal zones / trendlines.

Experiments (user request 2026-10-18):
  B  take-profit (all) at the nearest H4 zone ahead (buy: zone bottom above entry)
  C  take-profit HALF at that zone, rest keeps the original trailing stop
  D  skip the entry when that zone is closer than 1R (little room to run)
  E  D + C
  F  weighting: x1.5 size when an H4 correction line is broken or price is within 0.5 ATR(H4)
     of a live D1/H4 impulse line (reported as weighted R, same trades as A)
All checks use only bars closed at the entry (EnvRecognizer.state_at(entry bar open + 15 min)).
Cost 1.2 pip per trade. Usage: EA_M15_CACHE=<csv> python dow_strategy/ma_ea_zones_lines.py
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'core'))
import engine_m15 as E  # noqa: E402
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import EnvRecognizer  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402

COST = 1.2e-4
frames = {tf: load(tf) for tf in ('D1', 'H4', 'H1', 'M15')}
env = EnvRecognizer(frames)
h4atr = atr(frames['H4'])
m15 = frames['M15'].set_index('t')
m15_close = m15.c
m15_sma200 = m15.c.rolling(200).mean()
_cache = {}


def state(t):
    if t not in _cache:
        _cache[t] = env.state_at(t + pd.Timedelta(minutes=15))
    return _cache[t]


def dow_ok(t, side):
    d = 'up' if side == 1 else 'down'
    s = state(t)
    return s['H1']['trend'] == d and s['H4']['trend'] == d


def zone_ahead(t, side, entry):
    zs = state(t)['H4']['zones']
    if side == 1:
        c = [z['bottom'] for z in zs if z['bottom'] > entry]
        return min(c) if c else None
    c = [z['top'] for z in zs if z['top'] < entry]
    return max(c) if c else None


def est_risk(t, side):
    """Same initial-stop rule as the engine (M15 SMA200 +/- 10 pips, min 10 pips)."""
    entry, sma = m15_close[t], m15_sma200[t]
    base = sma - 1e-3 if side == 1 else sma + 1e-3
    sl = min(base, entry - 1e-3) if side == 1 else max(base, entry + 1e-3)
    return abs(entry - sl)


def room_ok(t, side):
    z = zone_ahead(t, side, m15_close[t])
    return z is None or abs(z - m15_close[t]) >= est_risk(t, side)


def tp_zone(t, side, entry, risk):
    return zone_ahead(t, side, entry)


def bonus(t, side):
    s = state(t)
    a = h4atr[env.last_closed('H4', t + pd.Timedelta(minutes=15))]
    px = m15_close[t]
    corr = any(l['cls'] == 'correction' and l['broken'] for l in s['H4']['lines'])
    imp = any(l['cls'] == 'impulse' and abs(l['value'] - px) <= 0.5 * a for tf in ('D1', 'H4') for l in s[tf]['lines'])
    return corr or imp


def metrics(tr, w=None):
    if not len(tr):
        return dict(n=0)
    r = (tr.R - COST / tr.risk).to_numpy()
    if w is not None:
        r = r * w
    pos = r > 0
    eq = np.cumsum(r)
    return dict(n=len(r), win=round(pos.mean(), 2), sumR=round(r.sum(), 1), PF=round(r[pos].sum() / max(1e-9, -r[~pos].sum()), 2),
                maxDD=round((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(), 1))


if __name__ == '__main__':
    runs = {
        'A 基準（H1・H4ダウ一致）': E.Config(extra_filter=dow_ok),
        'B ＋H4水平帯で全決済': E.Config(extra_filter=dow_ok, tp_fn=tp_zone),
        'C ＋H4水平帯で半分決済': E.Config(extra_filter=dow_ok, tp_fn=tp_zone, tp_half=True),
        'D ＋先の水平帯が1R未満なら見送り': E.Config(extra_filter=lambda t, s: dow_ok(t, s) and room_ok(t, s)),
        'E ＋D＋C': E.Config(extra_filter=lambda t, s: dow_ok(t, s) and room_ok(t, s), tp_fn=tp_zone, tp_half=True),
    }
    rows, trades = {}, {}
    for name, cfg in runs.items():
        tr = E.run_pair('EURUSD', cfg)
        trades[name] = tr
        rows[name] = metrics(tr)
        print(name, rows[name], flush=True)
    A = trades['A 基準（H1・H4ダウ一致）']
    w = np.array([1.5 if bonus(t, s) else 1.0 for t, s in zip(A.time, A.side)])
    rows['F ＋ライン根拠ありはロット1.5倍（Aと同じトレード）'] = metrics(A, w)
    rows['  うちライン根拠あり'] = metrics(A[w > 1])
    rows['  うちライン根拠なし'] = metrics(A[w == 1])
    for k in list(rows)[-3:]:
        print(k, rows[k])
    out = Path(__file__).with_name('results'); out.mkdir(exist_ok=True)
    pd.DataFrame(rows).T.to_csv(out / 'ma_ea_zones_lines_2025_2026.csv')
