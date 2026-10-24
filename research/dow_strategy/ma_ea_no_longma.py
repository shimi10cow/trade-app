"""Existing EA with the long-MA filters switched off, Dow direction instead (user idea 2026-10-19)."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ma_ea_zones_lines as M  # noqa: E402

E = M.E


def h1_ok(t, s):
    return M.state(t)['H1']['trend'] == ('up' if s == 1 else 'down')


def corr(t):
    return any(l['cls'] == 'correction' and l['broken'] for l in M.state(t)['H4']['lines'])


if __name__ == '__main__':
    runs = {
        '既存EAそのまま': E.Config(),
        '長期MAあり＋H1・H4ダウ（前回の基準）': E.Config(extra_filter=M.dow_ok),
        '長期MAなし＋ダウなし': E.Config(use_long_ma=False),
        '長期MAなし＋H1ダウ': E.Config(use_long_ma=False, extra_filter=h1_ok),
        '長期MAなし＋H1・H4ダウ': E.Config(use_long_ma=False, extra_filter=M.dow_ok),
    }
    rows = {}
    for name, cfg in runs.items():
        tr = E.run_pair('EURUSD', cfg)
        rows[name] = M.metrics(tr)
        c = [corr(t) for t in tr.time]
        rows[name + '｜H4調整ラインブレイク中'] = M.metrics(tr[c])
        print(name, rows[name], ' ｜ライン', rows[name + '｜H4調整ラインブレイク中'], flush=True)
    out = Path(__file__).with_name('results'); out.mkdir(exist_ok=True)
    pd.DataFrame(rows).T.to_csv(out / 'ma_ea_no_longma_2025_2026.csv')


def m15_line_broken_recent(bars=16):
    """An M15 trendline pointing against the trade broke within the last `bars` M15 bars (known by entry)."""
    m15 = M.env.tf['M15']
    brk = [x for x in m15['lines']['events'] if x['action'] == 'break']
    ldir = {ln['key']: ln['direction'] for ln in m15['lines']['lines']}
    idx = {t: i for i, t in enumerate(pd.to_datetime(m15['df'].t))}

    def f(t, side):
        i = idx.get(pd.Timestamp(t))
        d = 'up' if side == 1 else 'down'
        return i is not None and any(i - bars <= x['idx'] <= i and ldir.get(x['key']) != d for x in brk)
    return f


def dow_trail_pivots():
    """M15 Dow pivots (env_recognition v2: 1.9xATR7, outside-bar split) in the engine's ZigZag format.
    Every confirm/relocate is a row; confirm_time = open time of the bar whose close made it known."""
    m15 = M.env.tf['M15']
    t = pd.to_datetime(m15['df'].t)
    rows = [dict(kind='H' if e['kind'] == 'hi' else 'L', price=e['price'], confirm_time=t[e['available_idx']])
            for e in m15['res']['pivot_events']]
    return pd.DataFrame(rows)
