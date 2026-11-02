"""Parity test for the new trend EA (eas/nt.py) against the research result (2026-11-02).

Research reference (research/dow_strategy/trendlab/sx, work files in TRENDLAB): engine 'newall' trades (daily side + H1 MA75 slope),
then level bounce / MA20 distance / impulse filters (f_, h_ files), H4 opening (and slope for FX) from trendlab/h4f.py, exit
'sma200|h1sw1', and at most 2 open per symbol in time order. The live EA does all of it inside one engine run.
Usage: python -m mt5_ea.live.tests.parity_nt XAUUSD   (needs TRENDLAB work files; full-history Frames take a few minutes)
"""
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'research'))
from mt5_ea.live.core import Frames  # noqa: E402
from mt5_ea.live.eas import nt  # noqa: E402

TL = Path(os.environ.get('TRENDLAB', '/home/user/trendlab'))


def live_m15(sym):
    m = pd.read_pickle(TL / f'stoch/m15_{sym}.pkl').rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
    if sym == 'USDJPY':
        for z in 'ohlc':
            m[z] = m[z] / 100
    return m


def reference(sym):
    sys.path.insert(0, str(TL))
    import h4f
    h = pd.read_pickle(TL / f'sx/h_{sym}.pkl'); f = pd.read_pickle(TL / f'sx/f_{sym}.pkl'); f['time'] = pd.to_datetime(f.time)
    d = h.merge(f[['time', 'side', '帯', 'MA20距離']], on=['time', 'side'])
    d = d[(d.time >= '2005-06-01') & (d['帯'] == 0) & (d['MA20距離'] > -0.9) & (d['推進ATR'] <= 6)].copy()
    d['sym'] = sym; d = h4f.add(d, 'time')
    d = d[d['H4開き'] < 2.5]
    if sym in nt.SLOPE_SYMS:
        d = d[d['H4MA75傾き'] < 0.35]
    d['R'] = d['sma200|h1sw1']; d['ex'] = pd.to_datetime(d['exit|h1sw1']); d = d.sort_values('time')
    keep, op = [], []
    for i, r in d.iterrows():
        op = [e for e in op if e > r.time]
        if len(op) >= 2:
            continue
        op.append(r.ex); keep.append(i)
    return d.loc[keep, ['time', 'side', 'R', 'ex']].reset_index(drop=True)


def main(sym):
    cache = TL / f'live_frames_{sym}.pkl'
    m = live_m15(sym)
    if cache.exists():
        F = pickle.load(open(cache, 'rb'))
    else:
        F = Frames(m, '2005-01-01', h_days=10000, m_days=10000); pickle.dump(F, open(cache, 'wb'))
    res = nt.run(F, sym, m15=m, seed=False)
    mine = pd.concat([res['trades'], pd.DataFrame(res['open'])], ignore_index=True)
    mine['t'] = pd.to_datetime(mine.t); mine = mine[mine.t >= '2005-06-01'].reset_index(drop=True)
    ref = reference(sym)
    A = {(r.t, int(r.side)): r for r in mine.itertuples()}; B = {(r.time, int(r.side)): r for r in ref.itertuples()}
    both = sorted(set(A) & set(B)); only_live = sorted(set(A) - set(B)); only_ref = sorted(set(B) - set(A))
    dR = np.array([A[k].R - B[k].R for k in both]); dx = sum(pd.Timestamp(A[k].exit_t) != pd.Timestamp(B[k].ex) for k in both)
    print(f'{sym}: live {len(mine)} research {len(ref)} same entries {len(both)} only live {len(only_live)} only research {len(only_ref)}')
    print(f'  same entries: exit time differs {dx}, |dR| > 0.01: {(np.abs(dR) > 0.01).sum()}, max |dR| {np.abs(dR).max() if len(dR) else 0:.3f}')
    print(f'  totals: live {mine.R.sum():+.1f}R ({mine.R.mean():+.3f}/trade)  research {ref.R.sum():+.1f}R ({ref.R.mean():+.3f}/trade)')
    for k in only_live[:8]:
        print('  only live', k)
    for k in only_ref[:8]:
        print('  only research', k)
    out = TL / f'parity_nt_{sym}.pkl'; pd.to_pickle(dict(mine=mine, ref=ref), out)


if __name__ == '__main__':
    for s in sys.argv[1:] or nt.SYMBOLS:
        main(s)
