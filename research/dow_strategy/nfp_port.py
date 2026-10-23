"""Combo ④ with 'no new gold trades in the 48h before an NFP release' (and the same for all three pairs as a check)."""
import numpy as np, pandas as pd, pfx, combo_stable as CS, nfp_study as NS
keys4 = CS.P['④ ③＋US30（T・Q）']; X = CS.mk(keys4); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
i = NS.NFP.searchsorted(X.tt); nxt = NS.NFP[np.minimum(i, len(NS.NFP) - 1)]
pre = ((nxt - X.tt) <= pd.Timedelta('48h')) & (nxt > X.tt)
pfx.ev(X, keys4, label='④ 基準')
pfx.ev(X[~(pre & (X.pair == 'XAUUSD')).to_numpy()], keys4, label='④ 金だけ NFP 前48h は入らない')
pfx.ev(X[~(pre & X.pair.isin(['XAUUSD', 'USDJPY', 'EURUSD'])).to_numpy()], keys4, label='④ 3銘柄とも NFP 前48h は入らない')
g = X[pre & (X.pair == 'XAUUSD')]
print('外れる金のトレード:', len(g), '回', f"前半 {g[g.tt.dt.year <= 2015].R.sum():+.1f}R 後半 {g[g.tt.dt.year >= 2016].R.sum():+.1f}R")
