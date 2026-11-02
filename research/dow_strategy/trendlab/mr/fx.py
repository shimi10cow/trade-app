"""EURUSD / USDJPY mean reversion on H1 (2026-11): quick bounce exits (RSI(2) > 70 like M's best exit), many contexts.

H1 bars from the research M15 caches (UTC). Signal at an H1 close; entry at that close; cost per trade as the research.
Contexts: ALL; DSIDE = only the daily side (H4 close vs SMA1200); RANGE = H4 range score > 0.7 (env Env formula);
LOWVOL = ATR14(H1) below its 20-day median; sessions by UTC hour of the signal: ASIA 0-6, LDN 7-11, NY 12-16 (no 20-23 rollover).
Entries: R5 / R10 = RSI(2) < 5 / 10 (sells > 95 / 90); BB = close beyond the 20-bar 2-sigma band.
Exits at an H1 close: R70 = RSI(2) > 70 (sells < 30); MA5 = close back over SMA5; MID = back over the 20-bar mean. Max 24 bars.
Stops: 1.5 / 2.5 / 4 x ATR14(H1) from the entry (filled at the worse of stop and open).
"""
import sys, numpy as np, pandas as pd, numba as nb
sym = sys.argv[1]; COST = {'EURUSD': 1.2e-4, 'USDJPY': 1.5e-2}[sym]
SPLIT = pd.Timestamp('2016-01-01')
m = pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').set_index('time')
H = m.resample('1h', label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna()
o, h, l, c = (H[k].to_numpy() for k in ('open', 'high', 'low', 'close')); n = len(c); T = H.index
cs = pd.Series(c); dl = cs.diff(); up = dl.clip(lower=0).ewm(alpha=0.5).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=0.5).mean()
rsi = (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()
pc = np.r_[c[0], c[:-1]]; atr = pd.Series(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))).rolling(14).mean().to_numpy()
ma5 = cs.rolling(5).mean().to_numpy(); mid = cs.rolling(20).mean().to_numpy(); sd = cs.rolling(20).std().to_numpy()
volq = (pd.Series(atr) < pd.Series(atr).rolling(24 * 20).median()).to_numpy()
# H4 daily side and range score
h4 = m.resample('4h', label='left', closed='left').agg(dict(high='max', low='min', close='last')).dropna()
c4 = h4.close; pc4 = c4.shift(); tr4 = np.maximum(h4.high - h4.low, np.maximum((h4.high - pc4).abs(), (h4.low - pc4).abs())); tr4.iloc[0] = h4.high.iloc[0] - h4.low.iloc[0]
A4 = tr4.ewm(alpha=1 / 7, adjust=False).mean(); s75 = c4.rolling(75).mean()
parts = [1 - pd.Series(v).rolling(3000, min_periods=1500).rank(pct=True) for v in ((c4 - s75).abs() / A4, (s75 - s75.shift(10)).abs() / A4, c4.diff(50).abs() / c4.diff().abs().rolling(50).sum())]
RS = pd.concat(parts, axis=1).mean(axis=1).to_numpy(); side4 = np.sign(c4 - c4.rolling(1200).mean()).to_numpy()
k4 = np.searchsorted((h4.index + pd.Timedelta('4h')).to_numpy(), (T + pd.Timedelta('1h')).to_numpy(), side='right') - 1
RSh = np.where(k4 >= 0, RS[np.maximum(k4, 0)], np.nan); SDh = np.where(k4 >= 0, side4[np.maximum(k4, 0)], 0)
hr = T.hour.to_numpy()


@nb.njit(cache=True)
def sim(sig, side, o, h, l, c, rsi, ma5, mid, atr, k, exm, maxb, cost):
    n = len(c); outR = np.full(n, np.nan); busy = -1
    for i in range(n - 1):
        if not sig[i] or i <= busy or not np.isfinite(atr[i]): continue
        s = side[i]; en = c[i]; st = en - s * k * atr[i]; risk = k * atr[i]; xp = np.nan; j = i
        for j in range(i + 1, min(i + maxb + 1, n)):
            if s == 1 and l[j] <= st: xp = min(st, o[j]); break
            if s == -1 and h[j] >= st: xp = max(st, o[j]); break
            if exm == 0: done = (rsi[j] > 70) if s == 1 else (rsi[j] < 30)
            elif exm == 1: done = (c[j] - ma5[j]) * s > 0
            else: done = (c[j] - mid[j]) * s > 0
            if done: xp = c[j]; break
        if np.isnan(xp): xp = c[j]
        outR[i] = (xp - en) * s / risk - cost / risk; busy = j
    return outR


ctx = {'ALL': np.ones(n, bool), 'DSIDE': None, 'RANGE': RSh > 0.7, 'LOWVOL': volq, 'ASIA': (hr >= 0) & (hr <= 6), 'LDN': (hr >= 7) & (hr <= 11), 'NY': (hr >= 12) & (hr <= 16)}
ok = ~np.isin(hr, (20, 21, 22, 23)) & np.isfinite(atr) & np.isfinite(sd)
rows = []
for en_name in ('R5', 'R10', 'BB'):
    for s in (1, -1):
        if en_name == 'BB': raw = (c < mid - 2 * sd) if s == 1 else (c > mid + 2 * sd)
        else:
            lo = 5 if en_name == 'R5' else 10; raw = (rsi < lo) if s == 1 else (rsi > 100 - lo)
        for cx, cm in ctx.items():
            cm2 = (SDh == s) if cx == 'DSIDE' else cm
            sig = raw & cm2 & ok
            for exm, exn in enumerate(('R70', 'MA5', 'MID')):
                for k in (1.5, 2.5, 4.0):
                    R = sim(sig, np.full(n, s, np.int64), o, h, l, c, rsi, ma5, mid, atr, k, exm, 24, COST)
                    idx = np.where(np.isfinite(R))[0]
                    rows.append(pd.DataFrame(dict(sym=sym, cfg=f'{en_name}|{cx}|{exn}|{k}', side=s, t=T[idx], R=R[idx])))
d = pd.concat(rows, ignore_index=True); d['half'] = np.where(d.t < SPLIT, 1, 2)
d.to_pickle(f'/home/user/trendlab/mr/fx_{sym}.pkl'); print(sym, len(d), flush=True)
