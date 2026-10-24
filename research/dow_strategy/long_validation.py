"""Long-term validation 2003-2026 (EURUSD M15, Forex Tester data converted to broker time).

Configs (all ideas chosen on 2025-26 only -> 2003-2024 is out of sample):
  1 existing EA (canonical)                       4 no long MA + H1 Dow
  2 existing EA + Dow-pivot trailing              5 no long MA + H1 Dow + Dow-pivot trailing
  3 existing EA + H1 Dow                          6 no long MA, no Dow + Dow-pivot trailing
Cost 1.2 pip per trade. Results: results/long_*.csv and printed summary.
Usage: EA_M15_CACHE=<broker-time M15 csv> python dow_strategy/long_validation.py [config numbers...]
"""
import bisect
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'core'))
import engine_m15 as E  # noqa: E402
from env_recognition.data import load  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
from env_recognition.pivots import pivot_events  # noqa: E402

COST = 1.2e-4
OUT = Path(__file__).with_name('results')
OUT.mkdir(exist_ok=True)

t0 = time.time()
h1 = load('H1', 'long')
h1_trend = [b[0] for b in dow_trend.run(h1, 'H1')['bars']]
h1_close = list(pd.to_datetime(h1.t) + pd.Timedelta(hours=1))
m15 = load('M15', 'long')
mt = pd.to_datetime(m15.t)
trail = pd.DataFrame([dict(kind='H' if e['kind'] == 'hi' else 'L', price=e['price'], confirm_time=mt[e['available_idx']])
                      for e in pivot_events(m15)])
print(f'prep {time.time() - t0:.0f}s  H1 bars {len(h1)}  M15 pivots {len(trail)}', flush=True)


def h1_ok(t, side):
    """H1 Dow major trend known at the close of the entry M15 bar."""
    k = bisect.bisect_right(h1_close, t + pd.Timedelta(minutes=15)) - 1
    return k >= 0 and h1_trend[k] == ('up' if side == 1 else 'down')


CONFIGS = {
    1: ('既存EA', dict()),
    2: ('既存EA＋ダウ高安トレール', dict(trail_pivots=trail)),
    3: ('既存EA＋H1ダウ', dict(extra_filter=h1_ok)),
    4: ('長期MAなし＋H1ダウ', dict(use_long_ma=False, extra_filter=h1_ok)),
    5: ('長期MAなし＋H1ダウ＋ダウ高安トレール', dict(use_long_ma=False, extra_filter=h1_ok, trail_pivots=trail)),
    6: ('長期MAなし＋ダウ高安トレール（H1ダウなし）', dict(use_long_ma=False, trail_pivots=trail)),
}


def stats(r):
    if not len(r):
        return dict(n=0)
    w = r > 0
    eq = np.cumsum(r)
    return dict(n=len(r), win=round(w.mean(), 3), sumR=round(r.sum(), 1), avgR=round(r.mean(), 3),
                PF=round(r[w].sum() / max(1e-9, -r[~w].sum()), 3),
                maxDD=round((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(), 1))


if __name__ == '__main__':
    pick = [int(x) for x in sys.argv[1:]] or list(CONFIGS)
    for i in pick:
        name, kw = CONFIGS[i]
        t1 = time.time()
        tr = E.run_pair('EURUSD', E.Config(**kw))
        tr['Rc'] = tr.R - COST / tr.risk
        tr.to_csv(OUT / f'long_trades_{i}.csv', index=False)
        y = pd.to_datetime(tr.time).dt.year
        rows = {'全期間': stats(tr.Rc.to_numpy())}
        for lab, a, b in (('2003-2014', 2003, 2014), ('2015-2024', 2015, 2024), ('2025-2026', 2025, 2026)):
            rows[lab] = stats(tr.Rc[(y >= a) & (y <= b)].to_numpy())
        for yr in sorted(y.unique()):
            rows[str(yr)] = stats(tr.Rc[y == yr].to_numpy())
        pd.DataFrame(rows).T.to_csv(OUT / f'long_summary_{i}.csv')
        print(f'[{i}] {name}  ({time.time() - t1:.0f}s)', flush=True)
        for k in ('全期間', '2003-2014', '2015-2024', '2025-2026'):
            print('   ', k, rows[k], flush=True)
