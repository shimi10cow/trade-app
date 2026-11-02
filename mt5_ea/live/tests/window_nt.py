"""Live-window check for the new trend EA (2026-11-02): run eas/nt.py the way the runner does (last window_days of M15,
Frames warm-up warm_days, q75 history from the seed file) at many cut points, and compare the entries made in the last
`span` days before each cut with the full-history run (parity_nt output). Shows how often the short live window decides
differently from the long research run.
Usage: python -m mt5_ea.live.tests.window_nt XAUUSD [n_cuts]
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.core import Frames  # noqa: E402
from mt5_ea.live.eas import nt  # noqa: E402
from mt5_ea.live.registry import BY_KEY  # noqa: E402
from mt5_ea.live.tests.parity_nt import live_m15  # noqa: E402

TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))


def main(sym, n_cuts=12, span=120):
    e = BY_KEY[f'P@{sym}']; m = live_m15(sym); m['t'] = pd.to_datetime(m.t)
    full = pd.read_pickle(TL / f'parity_nt_{sym}.pkl')['mine']
    cuts = pd.date_range('2009-01-01', '2026-06-01', periods=n_cuts)
    same = diff_live = diff_full = 0; rows = []
    for cut in cuts:
        w = m[(m.t > cut - pd.Timedelta(days=e.window_days)) & (m.t <= cut)].reset_index(drop=True)
        start = w.t.iat[0] + pd.Timedelta(days=e.warm_days)
        F = Frames(w, start, h_days=e.warm_days, m_days=e.warm_days)
        r = nt.run(F, sym)
        got = pd.concat([r['trades'], pd.DataFrame(r['open'])], ignore_index=True)
        lo = cut - pd.Timedelta(days=span)
        g = {(pd.Timestamp(t), int(s)) for t, s in zip(got.t, got.side) if pd.Timestamp(t) > lo} if len(got) else set()
        f = {(pd.Timestamp(t), int(s)) for t, s in zip(full.t, full.side) if lo < pd.Timestamp(t) <= cut}
        same += len(g & f); diff_live += len(g - f); diff_full += len(f - g)
        rows.append((str(cut.date()), len(f), len(g & f), sorted(g - f)[:3], sorted(f - g)[:3]))
        print(rows[-1], flush=True)
    print(f'{sym}: entries in the last {span} days before {n_cuts} cuts: same {same}, only live window {diff_live}, only full run {diff_full}')


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 12)
