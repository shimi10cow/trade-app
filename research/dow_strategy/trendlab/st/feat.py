"""Short-term study: M15 features for one instrument (all causal: a value at bar i uses bars closed at or before i).

M15: SMA20/75/200, ATR14, stochastic (14, slow 3, D 3), ZigZag swings (1.9 x ATR7 on M15) with their confirm bar,
M15 dow direction (+1 after a close above the last confirmed swing high, -1 below the last swing low).
H1: SMA20/75, MA75 10-bar slope / ATR, efficiency ratio over 48 bars, 48-bar high / low.
H4: daily side (SMA1200), opening (SMA20-SMA75)/ATR14, MA75 10-bar slope / ATR.
Prices are in the cache's space (natural log for gold / indices, raw for FX).
"""
import sys, numpy as np, pandas as pd
sym = sys.argv[1]
m = pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').reset_index(drop=True)
o, h, l, c = (m[k].to_numpy(float) for k in ('open', 'high', 'low', 'close'))
n = len(m)
def atr(df, k, ew=True):
    pc = df.close.shift(); tr = np.maximum(df.high - df.low, np.maximum((df.high - pc).abs(), (df.low - pc).abs()))
    return tr.ewm(alpha=1 / k, adjust=False).mean()
f = pd.DataFrame(dict(time=m.time, o=o, h=h, l=l, c=c))
f['a15'] = atr(m, 14); a7 = atr(m, 7).to_numpy()
for k in (20, 75, 200): f[f'm{k}'] = m.close.rolling(k).mean()
lo14 = m.low.rolling(14).min(); hi14 = m.high.rolling(14).max()
fk = 100 * (m.close - lo14) / (hi14 - lo14).replace(0, np.nan)
f['K'] = fk.rolling(3).mean(); f['D'] = f.K.rolling(3).mean()

# ZigZag on M15: confirm a swing high when price falls 1.9*ATR7 below the running high
sh = np.full(n, np.nan); sl = np.full(n, np.nan); shp = np.full(n, np.nan); slp = np.full(n, np.nan)
dirn = 1; ext = h[0]; last_h = np.nan; last_l = np.nan; prev_h = np.nan; prev_l = np.nan
for i in range(1, n):
    th = 1.9 * a7[i]
    if dirn == 1:
        if h[i] >= ext: ext = h[i]
        elif l[i] <= ext - th: prev_h, last_h = last_h, ext; dirn = -1; ext = l[i]
    else:
        if l[i] <= ext: ext = l[i]
        elif h[i] >= ext + th: prev_l, last_l = last_l, ext; dirn = 1; ext = h[i]
    sh[i], sl[i], shp[i], slp[i] = last_h, last_l, prev_h, prev_l
f['sh'], f['sl'], f['shp'], f['slp'] = sh, sl, shp, slp
# M15 dow direction from closes through the last confirmed swings
dd = np.zeros(n); d = 0
for i in range(1, n):
    if np.isfinite(sh[i - 1]) and c[i] > sh[i - 1]: d = 1
    elif np.isfinite(sl[i - 1]) and c[i] < sl[i - 1]: d = -1
    dd[i] = d
f['dow15'] = dd

d = m.set_index('time')
def tf(rule, hrs):
    x = d.resample(rule, label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna()
    x['avail'] = x.index + pd.Timedelta(hours=hrs); return x
h1 = tf('1h', 1); a1 = atr(h1, 7)
h1f = pd.DataFrame(dict(avail=h1.avail, h1m20=h1.close.rolling(20).mean(), h1m75=h1.close.rolling(75).mean()))
h1f['h1sl'] = (h1f.h1m75 - h1f.h1m75.shift(10)) / a1
h1f['h1a'] = a1
h1f['h1er'] = (h1.close - h1.close.shift(48)).abs() / h1.close.diff().abs().rolling(48).sum()
h1f['h1hi'] = h1.high.rolling(48).max(); h1f['h1lo'] = h1.low.rolling(48).min()
h4 = tf('4h', 4); a4 = atr(h4, 14)
h4f = pd.DataFrame(dict(avail=h4.avail, side=np.sign(h4.close - h4.close.rolling(1200).mean()),
                        op4=(h4.close.rolling(20).mean() - h4.close.rolling(75).mean()) / a4,
                        sl4=(h4.close.rolling(75).mean() - h4.close.rolling(75).mean().shift(10)) / a4))
f['ct'] = f.time + pd.Timedelta(minutes=15)          # the M15 bar's close time
for x in (h1f, h4f):
    f = pd.merge_asof(f.sort_values('ct'), x.reset_index(drop=True).sort_values('avail'), left_on='ct', right_on='avail',
                      direction='backward').drop(columns='avail')
f = f.sort_values('time').reset_index(drop=True)
f.to_pickle(f'/home/user/trendlab/st/f_{sym}.pkl'); print(sym, n, flush=True)
