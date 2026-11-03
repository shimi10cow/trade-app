"""Parity test for the new return move EA (eas/rm.py) against the research run (trendlab/rm/run8.py rows, 2026-11-03).

Research reference: r8_{sym}.pkl rows with kind PRV, prior H4 trend >= 50 bars, trigger D, stop LO, exit M2, level break <= 0.5.
The research enforced one position per (variant, side) in setup order; the live EA does it in bar order -> a few entries may differ.
Usage: python -m mt5_ea.live.tests.parity_rm EURUSD XAUUSD   (needs TRENDLAB live_frames_{sym}.pkl and rm/r8_{sym}.pkl)
"""
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.eas import rm  # noqa: E402

TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))
RCOST = {'EURUSD': 1.2e-4, 'XAUUSD': 2.5e-4, 'USDJPY': 1.5e-4}


def main(sym):
    F = pickle.load(open(TL / f'live_frames_{sym}.pkl', 'rb'))
    res = rm.run(F)
    mine = res['trades'].copy(); mine['t'] = pd.to_datetime(mine.t)
    d = pd.read_pickle(TL / f'rm/r8_{sym}.pkl')
    ref = d[(d.kind == 'PRV') & (d.pre_bars >= 50) & (d.trig == 'D') & (d.stop == 'LO') & (d.ex == 'M2') & (d.brk <= 0.5)].copy()
    A = {(r.t, int(r.side)): r for r in mine.itertuples()}; B = {(r.t, int(r.side)): r for r in ref.itertuples()}
    both = sorted(set(A) & set(B)); ol = sorted(set(A) - set(B)); orf = sorted(set(B) - set(A))
    dx = sum(pd.Timestamp(A[k].exit_t) != pd.Timestamp(B[k].exit_t) for k in both)
    # same costs: live R uses F.COST; add back and subtract the research cost
    dR = np.array([(A[k].R + F.COST / A[k].risk - RCOST[sym] / A[k].risk) - B[k].R for k in both])
    print(f'{sym}: live {len(mine)} research {len(ref)} same {len(both)} only live {len(ol)} only research {len(orf)}')
    print(f'  same entries: exit time differs {dx}, |dR| > 0.01: {(np.abs(dR) > 0.01).sum()}, max |dR| {np.abs(dR).max() if len(dR) else 0:.3f}')
    print(f'  totals: live {mine.R.sum():+.1f}R ({mine.R.mean():+.3f}/trade, live cost)  research {ref.R.sum():+.1f}R ({ref.R.mean():+.3f})')
    for k in ol[:6]: print('  only live', k)
    for k in orf[:6]: print('  only research', k)


if __name__ == '__main__':
    for s in sys.argv[1:] or rm.ADOPTED:
        main(s)
