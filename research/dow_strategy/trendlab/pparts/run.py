"""Which parts of P carry its edge across markets? (2026-11-04) P's live code on broker-time data (5 markets), one part off at a time.
Parts: P's own entry conditions (daily side + H1 MA75 slope, MA20 depth, H4 opening, H4 slope for FX) and the base engine's
(the long-MA group = H1 SMA200 slope + SMA200/480 relation + q75 + MA-ABCD; q75 alone; SMA200 slope alone; only the 1st / 2nd pullback).
Output pparts/p_{sym}.pkl = {variant: trades(t, side, R)}.
"""
import pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.eas import nt as NT
sym = sys.argv[1]; IDX = sym in ('US500', 'US100')
F = pickle.load(open(f'/home/user/trendlab/idx/frames_{sym}.pkl' if IDX else f'/home/user/trendlab/tz/frames_{sym}.pkl', 'rb'))
NT.COST.setdefault(sym, 2e-4)
orig_cfg, orig_ss = NT.config, NT._daily_side_slope
def run(no=(), **eng):
    saved = dict(M20_MIN=NT.M20_MIN, OPEN_MAX=NT.OPEN_MAX, SLOPE_MAX=NT.SLOPE_MAX)
    if 'm20' in no: NT.M20_MIN = -1e9
    if 'open' in no: NT.OPEN_MAX = 1e9
    if 'slope4' in no: NT.SLOPE_MAX = 1e9
    if 'side' in no: NT._daily_side_slope = lambda m15: (lambda t, s: True)
    def cfg(*a, **k):
        c = orig_cfg(*a, **k)
        for kk, vv in eng.items(): setattr(c, kk, vv)
        return c
    NT.config = cfg
    try:
        tr = NT.run(F, sym, seed=False)['trades']
    finally:
        NT.config, NT._daily_side_slope = orig_cfg, orig_ss
        for kk, vv in saved.items(): setattr(NT, kk, vv)
    tr['t'] = pd.to_datetime(tr.t)
    return tr[tr.t >= ('2017-07-01' if IDX else '2005-06-01')][['t', 'side', 'R']].reset_index(drop=True)
V = {'P': {}, '日足の向き＋H1 MA75 傾き': dict(no=('side',)), 'MA20 から深すぎ': dict(no=('m20',)), 'H4 の開き': dict(no=('open',)),
     '長い MA のまとまり': dict(use_long_ma=False), 'q75 だけ': dict(q75_warmup=10 ** 9), 'SMA200 の傾きだけ': dict(s200_min=-1e9),
     '1・2 回目の押しだけ（3 回目も入る）': dict(max_entry_point=3), 'P の条件全部': dict(no=('side', 'm20', 'open', 'slope4'))}
if sym in NT.SLOPE_SYMS: V['H4 の傾き'] = dict(no=('slope4',))
out = {}
for k, kw in V.items():
    no = kw.pop('no', ()); out[k] = run(no, **kw); print(sym, k, len(out[k]), f'{out[k].R.mean():+.3f}', flush=True)
pd.to_pickle(out, f'/home/user/trendlab/pparts/p_{sym}.pkl')
