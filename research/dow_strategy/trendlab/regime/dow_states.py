"""Weekly / daily Dow states for the 8 symbols (2026-11), from the research M15 caches, known at each bar's close.
Per symbol, saved per D1 bar (value known when that D1 bar has closed):
  WM / WP : weekly major / provisional Dow trend (+1 up, -1 down, 0 none)
  DM / DP : daily major / provisional Dow trend
  W_in    : the last weekly close is between the last confirmed weekly swing high and swing low (a weekly range: neither broken)
  D_in    : the same on the daily
  Whi/Wlo, Dhi/Dlo: those confirmed swing levels
"""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition import dow_trend

SYMS = ['XAUUSD', 'EURUSD', 'USDJPY', 'US30', 'US500', 'JP225', 'XAGUSD', 'BTCUSD']
SG = {'up': 1, 'down': -1}


def frame(m, rule):
    x = m.resample(rule, label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna()
    if rule == '1D': x = x[x.index.dayofweek < 5]
    end = x.index + (pd.Timedelta('1D') if rule == '1D' else pd.Timedelta('7D'))
    return x.reset_index().rename(columns=dict(time='t', open='o', high='h', low='l', close='c')), end


def states(df, tf):
    R = dow_trend.run(df, tf); n = len(df)
    maj = np.array([SG.get(b[0], 0) for b in R['bars']]); prv = np.array([SG.get(b[0], 0) for b in R['prov_bars']])
    hi = np.full(n, np.nan); lo = np.full(n, np.nan); last = {'hi': np.nan, 'lo': np.nan}
    ev = sorted((e['available_idx'], e['kind'], e['price']) for e in R['pivot_events'] if e['action'] == 'confirm')
    j = 0
    for i in range(n):
        while j < len(ev) and ev[j][0] <= i: last[ev[j][1]] = ev[j][2]; j += 1
        hi[i], lo[i] = last['hi'], last['lo']
    c = df.c.to_numpy(); inside = (c <= hi) & (c >= lo)
    return maj, prv, hi, lo, inside


out = {}
for s in SYMS:
    m = pd.read_pickle(f'/home/user/trendlab/stoch/m15_{s}.pkl').set_index('time')
    D, Dend = frame(m, '1D'); W, Wend = frame(m, 'W-MON')
    dM, dP, dhi, dlo, din = states(D, 'D1'); wM, wP, whi, wlo, win = states(W, 'W1')
    day = pd.DataFrame(dict(DM=dM, DP=dP, Dhi=dhi, Dlo=dlo, D_in=din), index=pd.DatetimeIndex(Dend))
    wk = pd.DataFrame(dict(WM=wM, WP=wP, Whi=whi, Wlo=wlo, W_in=win), index=pd.DatetimeIndex(Wend))
    day.index.name = 'end'; wk.index.name = 'wend'
    day = pd.merge_asof(day.reset_index(), wk.reset_index(), left_on='end', right_on='wend', direction='backward').set_index('end')
    out[s] = day.dropna(subset=['WM']); print(s, len(day), day.WM.value_counts().to_dict(), round(day.W_in.mean(), 2), flush=True)
pd.to_pickle(out, '/home/user/trendlab/regime/dow_states.pkl')
