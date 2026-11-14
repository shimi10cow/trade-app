"""T2@EURUSD H4-line skip (2026-11-14, eas/h4lines.py, docs/OPEN_ITEMS.md D17) on the broker (server-time) EURUSD M15.

Research result (2005-2026): the old T2 has 362 trades (+4.12R a year); with the skip on the whole history 70 are skipped
and 7 new ones enter in the freed slots, 299 trades (+4.97R a year, max DD 12.2R).  Checks: the counts, and that no kept
trade has an alive H4 line ahead within 1R (an independent loop over the same lines).
Usage: python -m mt5_ea.live.tests.parity_t2lines
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.core import Frames  # noqa: E402
from mt5_ea.live.env import Env  # noqa: E402
from mt5_ea.live.eas import h4lines as H4L, rt as RT  # noqa: E402
from mt5_ea.live.eas.wave import axis_filter  # noqa: E402

TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))


def trades(F, env, sl_fn=None):
    tr = axis_filter(F, RT.run(F, 'T1t', env=env, sl_fn=sl_fn))['trades']
    tr = tr[tr.R.notna() & tr.exit_t.notna() & (tr.risk > 0)].copy(); tr['t'] = pd.to_datetime(tr.t)
    return tr.sort_values('t').reset_index(drop=True)


def main():
    m = pd.read_csv(TL / 'broker/EURUSD_M15.csv.gz', parse_dates=['time']).rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
    m = m[m.t >= '2004-01-01'].reset_index(drop=True); F = Frames(m, pd.Timestamp('2005-01-01')); env = Env(F.m15_all)
    old, new = trades(F, env), trades(F, env, H4L.near_skip(F, cutover=False))
    LN = H4L.lines(F); bad = 0
    for p in new.itertuples():
        al = LN[(LN.born <= p.t) & (LN.dead > p.t) & (LN.born > p.t - pd.Timedelta(days=H4L.DAYS))]
        ah = (al.p - p.entry) * p.side; ah = ah[ah > 0]
        bad += bool(len(ah) and ah.min() / p.risk <= H4L.MAX_R)
    y = lambda tr: (tr.t.max() - tr.t.min()).days / 365.25
    print(f'old T2 {len(old)} trades {old.R.sum() / y(old):+.2f}R/yr | with skip {len(new)} trades {new.R.sum() / y(new):+.2f}R/yr '
          f'| new entries {len(set(new.t) - set(old.t))} | kept trades with a line within 1R: {bad}')
    print('expected: 362 / 299, 7 new, 0 with a line within 1R')


if __name__ == '__main__':
    main()
