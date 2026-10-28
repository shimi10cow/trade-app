"""Dow width study: at each entry of a Dow EA, the width (bars) of the last completed swing on M15 / H1 / H4, known at that time."""
import sys, time, bisect
sys.path.insert(0, '/home/user/trade-app')
import numpy as np, pandas as pd
from mt5_ea.live.core import Frames, to_space
from mt5_ea.live.eas import j2 as J2, rt as RT
from mt5_ea.live.eas.wave import axis_filter
R = '/home/user/trade-app/'
def load(sym):
    d = pd.read_csv(R + f'{sym}_m1_M5.csv.gz', usecols=[0, 1, 2, 3, 4], parse_dates=['time'])
    d = d.set_index('time').resample('15min', label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna().reset_index()
    return pd.DataFrame(dict(t=d.time, o=to_space(sym, d.open), h=to_space(sym, d.high), l=to_space(sym, d.low), c=to_space(sym, d.close)))
def swing_lookup(Rk, close_times):
    """(available time, width of the last completed swing in bars) after every pivot event, causal (relocations included)."""
    piv = {}; out_t = []; out_w = []
    for e in sorted(Rk['pivot_events'], key=lambda e: e['available_idx']):
        piv[e['id']] = e['idx']
        ids = sorted(piv)[-2:]
        if len(ids) == 2:
            out_t.append(close_times[e['available_idx']]); out_w.append(piv[ids[1]] - piv[ids[0]])
    return out_t, out_w
def width_at(tt, lut):
    T, W = lut; j = bisect.bisect_right(T, tt) - 1
    return W[j] if j >= 0 else np.nan
runs = {'J2@USDJPY': ('USDJPY', lambda F: J2.run(F, **J2.ADOPTED['USDJPY'])), 'T2@EURUSD': ('EURUSD', lambda F: axis_filter(F, RT.run(F, 'T1t')))}
out = []
for key in sys.argv[1:]:
    sym, fn = runs[key]; t0 = time.time()
    F = Frames(load(sym), '2005-01-01')
    print(key, 'frames', f'{time.time() - t0:.0f}s', flush=True)
    tr = fn(F)['trades'].copy(); tr['tt'] = pd.to_datetime(tr.t)
    L15 = swing_lookup(F.R15, list(F.CL15)); L1 = swing_lookup(F.R1, F.C1); L4 = swing_lookup(F.R4, F.C4)
    tr['W15'] = [width_at(t, L15) for t in tr.tt]; tr['W1'] = [width_at(t, L1) for t in tr.tt]; tr['W4'] = [width_at(t, L4) for t in tr.tt]
    tr['key'] = key; out.append(tr[['key', 'tt', 'side', 'R', 'W15', 'W1', 'W4']])
    print(key, len(tr), 'trades', f'{time.time() - t0:.0f}s', flush=True)
pd.concat(out).to_pickle('/tmp/claude-0/-home-user-trade-app/13978ff6-6519-5f05-b953-f01dd0dd89a9/scratchpad/dow/dow_' + '_'.join(k.split('@')[0] for k in sys.argv[1:]) + '.pkl')
