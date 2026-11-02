"""Parity test for the H4 opening / slope gate (eas/h4gate.py, 2026-11-02).

Expected = the ungated live EA's full-history trades (TRENDLAB/port/p_{sym}.pkl, made by trendlab/port/run.py before the gate)
filtered with research trendlab/h4f.py; actual = the gated registry EA on the same data and start. They must be the same trades.
Usage: python -m mt5_ea.live.tests.parity_h4gate US30 XAGUSD JP225 USDJPY EURUSD
"""
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.core import Frames  # noqa: E402
from mt5_ea.live.env import Env  # noqa: E402
from mt5_ea.live.registry import ADOPTED  # noqa: E402

TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))
GATED = {'C@USDJPY': 'open', 'T@US30': 'open', 'Q@XAGUSD': 'open', 'Q@US30': 'open', 'DS@JP225': 'open', 'R@EURUSD': 'slope'}


def main(sym):
    sys.path.insert(0, str(TL)); import h4f
    m = pd.read_pickle(TL / f'stoch/m15_{sym}.pkl').rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
    if sym == 'USDJPY':
        for z in 'ohlc':
            m[z] = m[z] / 100
    start = str(max(pd.Timestamp('2005-06-01'), m.t.iat[0] + pd.Timedelta(days=250)).date())
    F = Frames(m, start, h_days=10000, m_days=10000); env = Env(F.m15_all)
    P = pd.read_pickle(TL / f'port/p_{sym}.pkl')
    for e in [x for x in ADOPTED if x.symbol == sym and x.key in GATED]:
        r = e.run(F, env); tr = pd.DataFrame(r['trades'])
        tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]
        got = set(zip(pd.to_datetime(tr[tc]), tr.side.astype(int)))
        got = {k for k in got if k[0] >= pd.Timestamp(start)}
        ref = h4f.add(P[P.key == e.key].copy(), 't')
        ref = ref[ref['H4開き' if GATED[e.key] == 'open' else 'H4MA75傾き'] < (2.5 if GATED[e.key] == 'open' else 0.35)]
        exp = set(zip(pd.to_datetime(ref.t), ref.side.astype(int)))
        R = tr[[(pd.Timestamp(t), int(s)) in got for t, s in zip(tr[tc], tr.side)]].R.sum()
        print(f'{e.key}: gated {len(got)} expected {len(exp)} same {len(got & exp)} only gated {len(got - exp)} only expected {len(exp - got)}'
              f'  total R gated {R:+.1f} expected {ref.R.sum():+.1f}', flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:]:
        main(s)
