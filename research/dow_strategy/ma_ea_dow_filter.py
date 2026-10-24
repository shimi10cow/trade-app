"""Existing MA+Stochastic EA (research/core/engine_m15.py, unchanged rules) + Dow environment filters.

Filter is evaluated at the signal bar CLOSE (entry time) with EnvRecognizer.state_at(bar open + 15 min),
i.e. only bars closed by the entry. Cost: 1.2 pip per trade (EURUSD spread, user 2026-10-18).
Usage: EA_M15_CACHE=<csv> python dow_strategy/ma_ea_dow_filter.py
"""
import os
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'core'))
import engine_m15 as E  # noqa: E402
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import EnvRecognizer  # noqa: E402

COST = 1.2e-4
env = EnvRecognizer({tf: load(tf) for tf in ('D1', 'H4', 'H1', 'M15')})
_cache = {}


def state(t):
    if t not in _cache:
        _cache[t] = env.state_at(t + pd.Timedelta(minutes=15))
    return _cache[t]


def agree(tf, key='trend'):
    return lambda t, side: (state(t)[tf] or {}).get(key) == ('up' if side == 1 else 'down')


FILTERS = {
    'なし（既存EAそのまま）': None,
    'H1ダウ一致': agree('H1'),
    'H4ダウ一致': agree('H4'),
    'D1ダウ一致': agree('D1'),
    'H1仮一致': agree('H1', 'prov_trend'),
    'H4仮一致': agree('H4', 'prov_trend'),
    'H1かつH4ダウ一致': lambda t, s: agree('H1')(t, s) and agree('H4')(t, s),
    'H4調整ラインブレイク中': lambda t, s: any(l['cls'] == 'correction' and l['broken'] for l in state(t)['H4']['lines']),
}


def metrics(tr):
    if not len(tr):
        return dict(n=0)
    r = tr.R - COST / tr.risk
    w = r > 0
    eq = r.cumsum()
    return dict(n=len(r), win=round(w.mean(), 2), sumR=round(r.sum(), 1), PF=round(r[w].sum() / max(1e-9, -r[~w].sum()), 2),
                maxDD=round((eq - eq.cummax()).min(), 1))


if __name__ == '__main__':
    rows = {}
    for name, f in FILTERS.items():
        tr = E.run_pair('EURUSD', E.Config(extra_filter=f))
        rows[name] = metrics(tr)
        print(name, rows[name], flush=True)
    out = Path(__file__).with_name('results'); out.mkdir(exist_ok=True)
    pd.DataFrame(rows).T.to_csv(out / 'ma_ea_dow_filter_2025_2026.csv')
