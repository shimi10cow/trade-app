"""Whole-portfolio review (2026-11): every live EA of one symbol on the full history (current registry: gates on, R included for
reference), with entry / stop, P's entry features and an exit variant; plus P itself on symbols it does not trade yet.

Features at the trade's time t (the EA's own 't'; side s): daily side (H4 close vs SMA1200), H1 MA75 10-bar slope / EWM ATR7,
level bounce (nt._levels, at t + 15 min), H1 MA20 distance, impulse since the H1 regime began (nt._impulse), H4 opening / slope.
Exit variant 'h1a1': same entry and initial stop, from +1R trail to confirmed H1 swings below (above) the close (P's exit),
30-day cap like the research sims; cost as the EA's own R (live core 1.2e-4 in the price space).
"""
import os, sys, pickle, time
import numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research'); sys.path.insert(0, '/home/user/trade-app/research/core')
from mt5_ea.live.core import Frames
from mt5_ea.live.env import Env
from mt5_ea.live.registry import ADOPTED
from mt5_ea.live.eas import nt as NT
from env_recognition.pivots import pivot_events
import engine_m15 as EM

sym = sys.argv[1]; t0 = time.time(); TL = '/home/user/trendlab'
m = pd.read_pickle(f'{TL}/stoch/m15_{sym}.pkl').rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
if sym == 'USDJPY':
    for z in 'ohlc': m[z] = m[z] / 100
cache = f'{TL}/live_frames_{sym}.pkl'
if os.path.exists(cache):
    F = pickle.load(open(cache, 'rb'))
else:
    start = str(max(pd.Timestamp('2005-01-01'), m.t.iat[0] + pd.Timedelta(days=250)).date())
    F = Frames(m, start, h_days=10000, m_days=10000); pickle.dump(F, open(cache, 'wb'))
print(sym, 'frames', round(time.time() - t0), flush=True)
env = Env(F.m15_all)
# features
d = m.rename(columns=dict(t='time', o='open', h='high', l='low', c='close'))[['time', 'open', 'high', 'low', 'close']].copy(); d['time'] = pd.to_datetime(d.time)
EM.load_m15 = lambda p: d.copy(); mm, h1, _, _, _ = EM.build_features('EURUSD')
imp = NT._impulse(mm, h1); lev = NT._levels(F); shape = NT.h4_shape(m)
h1b = NT._bars(m, '1h'); pc = h1b.c.shift(); tr = np.maximum(h1b.h - h1b.l, np.maximum((h1b.h - pc).abs(), (h1b.l - pc).abs()))
a1 = tr.ewm(alpha=1 / 7, adjust=False).mean(); sl75 = ((h1b.c.rolling(75).mean() - h1b.c.rolling(75).mean().shift(10)) / a1).to_numpy(); C1 = h1b.cl.to_numpy()
h4b = NT._bars(m, '4h'); sideD = np.sign(h4b.c - h4b.c.rolling(1200).mean()).to_numpy(); C4 = h4b.cl.to_numpy()
T = mm.time.to_numpy(); H = mm.high.to_numpy(); L = mm.low.to_numpy(); C = mm.close.to_numpy(); n = len(C)
h1r = h1.reset_index(drop=True); Ch = h1r.avail_time.to_numpy()
ev = pivot_events(h1r.rename(columns=dict(open='o', high='h', low='l', close='c'))[['o', 'h', 'l', 'c']])
HP = sorted((Ch[e['available_idx']], 'L' if e['kind'] == 'lo' else 'H', e['price']) for e in ev if e['action'] == 'confirm')
HPT = np.array([a for a, _, _ in HP]); HPK = np.array([b for _, b, _ in HP]); HPP = np.array([c for _, _, c in HP])


def sim_h1(i, s, en, sl):
    risk = (en - sl) * s; on = False
    for j in range(i + 1, min(n, i + 96 * 30)):
        if (L[j] <= sl) if s == 1 else (H[j] >= sl): return (sl - en) * s / risk, T[j]
        if not on and (((H[j] - en) if s == 1 else (en - L[j])) >= risk): on = True
        if on:
            k = np.searchsorted(HPT, T[j], side='left') - 1; want = 'L' if s == 1 else 'H'
            while k >= 0 and HPK[k] != want: k -= 1
            if k >= 0 and (HPP[k] - sl) * s > 0 and (HPP[k] - C[j]) * s < 0: sl = HPP[k]
    j = min(n, i + 96 * 30) - 1; return (C[j] - en) * s / risk, T[j]


def features(t, s):
    t = pd.Timestamp(t); tn = np.datetime64(t)
    k1 = np.searchsorted(C1, tn, side='right') - 1; k4 = np.searchsorted(C4, tn, side='right') - 1
    hit, m20d = lev(t + pd.Timedelta('15min'), s); op, s4 = shape(t, s)
    return dict(dside=float(sideD[k4] == s) if k4 >= 0 else np.nan, h1sl=sl75[k1] * s if k1 >= 0 else np.nan, band=float(hit), m20d=m20d,
                imp=imp(t, s), op=op, sl4=s4)


out = []
eas = [(e.key, e.run) for e in ADOPTED if e.symbol == sym]
COSTP = {'US500': 2e-4, 'JP225': 3e-4, 'US30': 1.5e-4, 'XAGUSD': 8e-4, 'BTCUSD': 8e-4}
if sym not in NT.SYMBOLS:                                          # P on a symbol it does not trade yet
    NT.COST[sym] = COSTP.get(sym, 1.2e-4)
    eas.append((f'P@{sym}', lambda F_, env_: NT.run(F_, sym, m15=m, seed=False)))
for key, fn in eas:
    try:
        r = fn(F, env); tr = pd.concat([pd.DataFrame(r['trades']), pd.DataFrame(r['open'])], ignore_index=True)
    except Exception as ex:
        import traceback; traceback.print_exc(); continue
    if not len(tr): continue
    tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]; ec = [c for c in ('exit_t', 'ExitTime') if c in tr][0]
    tr = tr.assign(t=pd.to_datetime(tr[tc]), exit_t=pd.to_datetime(tr[ec])); tr = tr[(tr.t >= '2005-06-01') & tr.R.notna()].reset_index(drop=True)
    if 'open_end' in tr: tr = tr[~tr.open_end.fillna(False).astype(bool)]
    if key.startswith('S@BTC'): tr = tr[tr.t.dt.dayofweek < 5]
    sl0 = tr['sl0'] if 'sl0' in tr else tr.get('initial_sl')
    for x, s0 in zip(tr.itertuples(), sl0):
        s = int(x.side); f = dict(key=key, sym=sym, t=x.t, exit_t=x.exit_t, side=s, R=float(x.R), entry=float(x.entry), sl0=float(s0))
        f.update(features(x.t, s))
        i = int(np.searchsorted(T, np.datetime64(x.t)))
        if i < n and (f['entry'] - f['sl0']) * s > 0:
            R2, x2 = sim_h1(i, s, f['entry'], f['sl0']); f['R_h1'] = R2 - 1.2e-4 / ((f['entry'] - f['sl0']) * s); f['exit_h1'] = x2
        out.append(f)
    print(sym, key, len(tr), round(tr.R.sum(), 1), round(time.time() - t0), flush=True)
pd.DataFrame(out).to_pickle(f'{TL}/full/t_{sym}.pkl'); print('done', sym, round(time.time() - t0), flush=True)
