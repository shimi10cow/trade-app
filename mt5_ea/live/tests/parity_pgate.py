"""Parity test for eas/pgate.py (2026-11): the gated registry EA must give exactly the research trades
(TRENDLAB/full/t_{sym}.pkl, made before the gate) minus the ones the gate rule removes (impulse > 6 / level bounce).
Usage: python -m mt5_ea.live.tests.parity_pgate EURUSD US30
"""
import os
import pickle
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.env import Env  # noqa: E402
from mt5_ea.live.registry import BY_KEY  # noqa: E402

TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))
RULE = {'C@EURUSD': lambda x: ~(x.imp > 6), 'A@EURUSD': lambda x: ~(x.imp > 6), 'T@US30': lambda x: x.band == 0}


def main(sym):
    F = pickle.load(open(TL / f'live_frames_{sym}.pkl', 'rb')); env = Env(F.m15_all)
    ref = pd.read_pickle(TL / f'full/t_{sym}.pkl')
    for key, rule in RULE.items():
        if not key.endswith(sym):
            continue
        r = BY_KEY[key].run(F, env)
        tr = pd.concat([pd.DataFrame(r['trades']), pd.DataFrame(r['open'])], ignore_index=True)
        tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]
        got = {(pd.Timestamp(t), int(s)) for t, s in zip(tr[tc], tr.side) if pd.Timestamp(t) >= pd.Timestamp('2005-06-01')}
        g = ref[ref.key == key]; g = g[rule(g)]
        exp = {(pd.Timestamp(t), int(s)) for t, s in zip(g.t, g.side)}
        Rg = tr[[(pd.Timestamp(t), int(s)) in got for t, s in zip(tr[tc], tr.side)]].R.sum()
        print(f'{key}: gated {len(got)} expected {len(exp)} same {len(got & exp)} only gated {len(got - exp)} only expected {len(exp - got)}'
              f'  total R {Rg:+.1f} expected {g.R.sum():+.1f}', flush=True)


if __name__ == '__main__':
    for s in sys.argv[1:]:
        main(s)
