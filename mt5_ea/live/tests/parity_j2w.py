"""J2@USDJPY weekly-trend version (2026-11-04) against the research set (RESEARCH_LOG §174: no hour window, weekly major Dow trend
the trade's way, weekly states from trendlab/regime/dow_states.py on the research M15). Weekly bars here = the full-history M15
resampled to W-MON weeks (the live runner uses the broker's W1 bars).  Usage: python -m mt5_ea.live.tests.parity_j2w
"""
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.registry import BY_KEY  # noqa: E402

TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))


def main():
    F = pickle.load(open(TL / 'live_frames_USDJPY.pkl', 'rb'))
    m = F.m15_all.set_index('t')
    F.W1 = m.resample('W-MON', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    tr = BY_KEY['J2@USDJPY'].run(F, None)['trades']; tr['t'] = pd.to_datetime(tr.t); tr = tr[tr.t >= '2005-06-01']
    J = pd.read_pickle(TL / 'audit/jt_USDJPY.pkl')['時間帯なし']
    DS = pd.read_pickle(TL / 'regime/dow_states.pkl')['USDJPY']
    idx = np.clip(DS.index.searchsorted(J.t, side='right') - 1, 0, None); ref = J[DS.WM.to_numpy()[idx] * J.side.to_numpy() == 1]
    a, b = set(zip(tr.t, tr.side)), set(zip(ref.t, ref.side))
    print(f'live {len(tr)} research {len(ref)} same {len(a & b)} only live {len(a - b)} only research {len(b - a)}')
    print(f'live {tr.R.mean():+.3f}R total {tr.R.sum():+.1f}R | research {ref.R.mean():+.3f}R total {ref.R.sum():+.1f}R')


if __name__ == '__main__':
    main()
