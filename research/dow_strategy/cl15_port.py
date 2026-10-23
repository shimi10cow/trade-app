"""Combo ④ with USDJPY C filtered by line strength (correction > 24 M15 bars and slope > 0.03 ATR/bar), alone and with the
USDJPY steep-H1-break block (§83)."""
import numpy as np, pandas as pd, pfx, combo_stable as CS
S = CS.S
d = pd.read_csv(f'{S}/ws_USDJPY/research/dow_strategy/results/step2/C_feat.csv'); d = d[(d.dur > 24) & (d.slope > 0.03)]
cj = pd.DataFrame(dict(R=d.R - 0.3e-4 / d.risk, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), key='C@USDJPY', pair='USDJPY', side=d.side))
keys4 = CS.P['④ ③＋US30（T・Q）']; X = CS.mk(keys4); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
pfx.ev(X, keys4, label='④ 基準')
Y = pd.concat([X[X.key != 'C@USDJPY'], cj], ignore_index=True)
pfx.ev(Y, keys4, label='④ ドル円C を線の強さで絞る')
BR = pd.read_pickle(f'{S}/feat/steep_breaks_USDJPY.pkl'); b = BR[(BR.slope >= 0.1) & (BR.away >= 2) & (BR.age >= 10)]
side = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl')[['key', 'tt', 'side']].assign(tt=lambda d: pd.to_datetime(d.tt)).drop_duplicates(['key', 'tt'])
Y = Y.drop(columns=['side'], errors='ignore').merge(side, on=['key', 'tt'], how='left'); Y.loc[Y.key == 'C@USDJPY', 'side'] = cj.side.to_numpy()[:0].tolist() or Y.loc[Y.key == 'C@USDJPY', 'side']
blk = np.zeros(len(Y), bool)
for sd in (1, -1):
    bt = b[b.side == sd].t.to_numpy(); m = ((Y.side == sd) & (Y.pair == 'USDJPY')).to_numpy(); tt = Y.tt.to_numpy()[m]
    j = np.searchsorted(bt, tt, 'right') - 1; ok = (j >= 0) & ((tt - bt[np.maximum(j, 0)]) <= np.timedelta64(48, 'h')); blk[np.nonzero(m)[0][ok]] = True
pfx.ev(Y[~blk], keys4, label='④ ＋ドル円 急角度ライン割れ後48h 入らない')
