"""M (RSI(2) pullback) widened (2026-11): instruments x timeframe (D1 / H4) x RSI level x exit x stop.

Bars from the research M15 caches (log prices for indices / metals / BTC, FX as quoted, USDJPY in yen).
Signal at a bar close: trend side = close above (below) the SMA200 of the same timeframe; RSI(2) (Wilder-ish EWM alpha 1/2, as
eas/rsi2.py) below lo (above 100-lo for sells). Buys only on US30 / US500 / JP225 / BTCUSD, both sides on FX / metals.
Entry at that close. Stops: k x ATR14 (k = 2.5 / 1.5 / 1.0) or the lowest low of the last 3 bars - 0.2 ATR ('sw3').
Exits at a close: above SMA5 ('ma5') or RSI(2) > 70 ('r70'), at most 'mx' bars (D1 10 / H4 30). Stop filled at min(stop, open).
R = move / risk - cost / risk (research costs per symbol).
"""
import sys, numpy as np, pandas as pd
sym = sys.argv[1]
COST = {'EURUSD': 1.2e-4, 'USDJPY': 1.5e-2, 'XAUUSD': 2.5e-4, 'XAGUSD': 8e-4, 'US30': 1.5e-4, 'US500': 2e-4, 'JP225': 3e-4, 'BTCUSD': 8e-4}[sym]
BUY_ONLY = sym in ('US30', 'US500', 'JP225', 'BTCUSD')
m = pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').set_index('time')
rows = []
for tf, rule, mx in (('D1', '1D', 10), ('H4', '4h', 30)):
    D = m.resample(rule, label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna()
    if tf == 'D1': D = D[D.index.dayofweek < 5]
    o, h, l, c = (D[k].to_numpy() for k in ('open', 'high', 'low', 'close')); n = len(c); T = D.index
    cs = pd.Series(c); dl = cs.diff(); up = dl.clip(lower=0).ewm(alpha=0.5).mean(); dn = (-dl.clip(upper=0)).ewm(alpha=0.5).mean()
    rsi = (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()
    pc = np.r_[c[0], c[:-1]]; atr = pd.Series(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))).rolling(14).mean().to_numpy()
    ma5 = cs.rolling(5).mean().to_numpy(); ma200 = cs.rolling(200).mean().to_numpy()
    lo3 = pd.Series(l).rolling(3).min().to_numpy(); hi3 = pd.Series(h).rolling(3).max().to_numpy()
    for lo in (5, 10, 20):
        for s in ((1,) if BUY_ONLY else (1, -1)):
            sig = np.where((c - ma200) * s > 0, (rsi < lo) if s == 1 else (rsi > 100 - lo), False) & np.isfinite(atr)
            for stn in ('a25', 'a15', 'a10', 'sw3'):
                for exn in ('ma5', 'r70'):
                    i = 0
                    while i < n - 1:
                        if not sig[i]: i += 1; continue
                        en = c[i]
                        st = en - s * {'a25': 2.5, 'a15': 1.5, 'a10': 1.0}.get(stn, 0) * atr[i] if stn != 'sw3' else ((lo3[i] - 0.2 * atr[i]) if s == 1 else (hi3[i] + 0.2 * atr[i]))
                        risk = (en - st) * s
                        if not risk > 0.2 * atr[i]: i += 1; continue
                        xp = None; j = i
                        for j in range(i + 1, min(i + mx + 1, n)):
                            if (l[j] <= st) if s == 1 else (h[j] >= st): xp = min(st, o[j]) if s == 1 else max(st, o[j]); break
                            done = ((c[j] - ma5[j]) * s > 0) if exn == 'ma5' else ((rsi[j] > 70) if s == 1 else (rsi[j] < 30))
                            if done: xp = c[j]; break
                        if xp is None: xp = c[j]
                        rows.append(dict(sym=sym, tf=tf, lo=lo, stop=stn, ex=exn, side=s, t=T[i], exit_t=T[j] + pd.Timedelta(rule), bars=j - i,
                                         R=(xp - en) * s / risk - COST / risk, riskp=risk / atr[i]))
                        i = j + 1
pd.DataFrame(rows).to_pickle(f'/home/user/trendlab/mr/m_{sym}.pkl'); print(sym, len(rows), flush=True)
