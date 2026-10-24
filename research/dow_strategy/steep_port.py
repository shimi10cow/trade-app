"""USDJPY: block entries for N h after a steep H1 line break in that direction (k=0.1 ATR/bar, ran >= 2 ATR away, line
age >= 10 bars) -> combo ④ same-risk check. Settings fixed from the USDJPY first half."""
import numpy as np, pandas as pd, pfx, combo_stable as CS
S = CS.S; BR = pd.read_pickle(f'{S}/feat/steep_breaks_USDJPY.pkl'); b = BR[(BR.slope >= 0.1) & (BR.away >= 2) & (BR.age >= 10)]
keys4 = CS.P['④ ③＋US30（T・Q）']; X = CS.mk(keys4); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
side = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl')[['key', 'tt', 'side']].assign(tt=lambda d: pd.to_datetime(d.tt)).drop_duplicates(['key', 'tt'])
X = X.merge(side, on=['key', 'tt'], how='left')
pfx.ev(X, keys4, label='④ 基準')
for N in (24, 48):
    blk = np.zeros(len(X), bool)
    for sd in (1, -1):
        bt = b[b.side == sd].t.to_numpy(); m = ((X.side == sd) & (X.pair == 'USDJPY')).to_numpy(); tt = X.tt.to_numpy()[m]
        j = np.searchsorted(bt, tt, 'right') - 1; ok = (j >= 0) & ((tt - bt[np.maximum(j, 0)]) <= np.timedelta64(N, 'h'))
        blk[np.nonzero(m)[0][ok]] = True
    g = X[blk]; print(f'N={N}: 外れるドル円のトレード {blk.sum()} 回', g.groupby(['key', g.tt.dt.year <= 2015]).R.sum().round(1).to_dict())
    pfx.ev(X[~blk], keys4, label=f'④ ドル円 急角度ライン割れ後{N}h 入らない')
