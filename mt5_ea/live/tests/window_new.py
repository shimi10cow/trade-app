"""Live-window check for the 2026-11-07 EAs (DL@EURUSD / DL@USDJPY / HL@EURUSD / Q@BTCUSD / Q@XAGUSD): run each one the way the
runner does (last window_days of M15, Frames warm-up warm_days) at several cut points and compare the entries in the last `span`
days before each cut with the full-history run.
Usage: python -m mt5_ea.live.tests.window_new DL@EURUSD [n_cuts]
"""
import os
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.core import Frames  # noqa: E402
from mt5_ea.live.env import Env  # noqa: E402
from mt5_ea.live.registry import BY_KEY  # noqa: E402

TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))


def main(key, n_cuts=8, span=120):
    e = BY_KEY[key]; sym = e.symbol
    FF = pickle.load(open(TL / 'tz' / f'frames_{sym}.pkl', 'rb')); m = FF.m15_all.copy(); m['t'] = pd.to_datetime(m.t)
    r = e.run(FF, Env(FF.m15_all)); full = pd.concat([r['trades'], pd.DataFrame(r['open'])], ignore_index=True)
    first = pd.Timestamp('2019-01-01' if sym == 'BTCUSD' else '2009-01-01')
    cuts = pd.date_range(first, m.t.iat[-1] - pd.Timedelta(days=30), periods=n_cuts)
    same = only_w = only_f = 0
    for cut in cuts:
        w = m[(m.t > cut - pd.Timedelta(days=e.window_days)) & (m.t <= cut)].reset_index(drop=True)
        F = Frames(w, w.t.iat[0] + pd.Timedelta(days=e.warm_days), h_days=e.warm_days, m_days=e.warm_days)
        g0 = e.run(F, Env(w)); got = pd.concat([g0['trades'], pd.DataFrame(g0['open'])], ignore_index=True)
        lo = cut - pd.Timedelta(days=span)
        g = {(pd.Timestamp(t), int(s)) for t, s in zip(got.t, got.side) if pd.Timestamp(t) > lo} if len(got) else set()
        f = {(pd.Timestamp(t), int(s)) for t, s in zip(full.t, full.side) if lo < pd.Timestamp(t) <= cut}
        same += len(g & f); only_w += len(g - f); only_f += len(f - g)
        print(str(cut.date()), 'full', len(f), 'same', len(g & f), 'only window', sorted(g - f)[:2], 'only full', sorted(f - g)[:2], flush=True)
    print(f'{key}: entries in the last {span} days before {n_cuts} cuts: same {same}, only live window {only_w}, only full run {only_f}')


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8)
