"""Candidate set after the 2026-10-23 cycles, same-risk comparison against combo ④."""
import numpy as np, pandas as pd, pfx, combo_stable as CS, new_summary as N
S = CS.S
keys4 = CS.P['④ ③＋US30（T・Q）']; X = CS.mk(keys4); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
c = ['R', 'tt', 'et', 'key', 'pair']
d = pd.read_csv(f'{S}/ws_USDJPY/research/dow_strategy/results/step2/C_feat.csv'); d = d[(d.dur > 24) & (d.slope > 0.03)]
CJ = pd.DataFrame(dict(R=d.R - 0.3e-4 / d.risk, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), key='C@USDJPY', pair='USDJPY'))
g = pd.read_csv(f'{S}/ws_XAUUSD/research/dow_strategy/results/step2/C_feat_loose.csv'); g = g[g.touch >= 2]
CT = pd.DataFrame(dict(R=g.R - 1.3e-4 / g.risk, tt=pd.to_datetime(g.t), et=pd.to_datetime(g.exit_t), key='CT@XAUUSD', pair='XAUUSD'))
M2 = pd.concat([N.load(s, 'rsi2/M_200_10_ma5_st.csv').assign(key=f'M@{s}', pair=s) for s in ('US30', 'US500')])[c]
JL = N.load('JP225', 'tl_N2.csv').assign(key='L@JP225', pair='JP225')[c]
base_noC = X[X.key != 'C@USDJPY'][c]
pfx.ev(X, keys4, label='④ 基準')
pfx.ev(base_noC, keys4, CJ, label='④ ドル円C絞る')
pfx.ev(base_noC, keys4, pd.concat([CJ, M2]), label='④ ドル円C絞る＋指数RSI2')
pfx.ev(base_noC, keys4, pd.concat([CJ, M2, JL]), label='④ ＋日経L')
pfx.ev(base_noC, keys4, pd.concat([CJ, M2, JL, CT]), label='④ ＋金 タッチ2回以上の調整ライン')
