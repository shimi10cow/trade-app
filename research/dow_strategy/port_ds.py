"""Right-shoulder EA (ds_ea.py, H1 trend break, stop above the left shoulder, 2R target, pullback >= 4 ATR H4) added to the
current candidate (④ with USDJPY C filtered + US30/US500 RSI(2)), same-risk comparison."""
import numpy as np, pandas as pd, pfx, combo_stable as CS, new_summary as N
S = CS.S
keys4 = CS.P['④ ③＋US30（T・Q）']; X = CS.mk(keys4); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
c = ['R', 'tt', 'et', 'key', 'pair']
d = pd.read_csv(f'{S}/ws_USDJPY/research/dow_strategy/results/step2/C_feat.csv'); d = d[(d.dur > 24) & (d.slope > 0.03)]
CJ = pd.DataFrame(dict(R=d.R - 0.3e-4 / d.risk, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), key='C@USDJPY', pair='USDJPY'))
M2 = pd.concat([N.load(s, 'rsi2/M_200_10_ma5_st.csv').assign(key=f'M@{s}', pair=s) for s in ('US30', 'US500')])[c]
base = X[X.key != 'C@USDJPY'][c]
EXTRA = {'EURUSD': 0.0, 'USDJPY': 0.3e-4, 'XAUUSD': 1.3e-4}      # same cost adjustments as port_final3


def ds(sym, depth=4.0):
    if sym in N.COST:
        x = N.load(sym, 'ds/DS_H1_left_tp2.csv')
        f = f'{S}/ws_{sym}/research/dow_strategy/results/ds/DS_H1_left_tp2.csv'
    else:
        f = ('/home/user/trade-app/research/dow_strategy/results' if sym == 'EURUSD' else f'{S}/ws_{sym}/research/dow_strategy/results') + '/ds/DS_H1_left_tp2.csv'
        d = pd.read_csv(f); x = pd.DataFrame(dict(tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), R=d.R - EXTRA[sym] / d.risk))
    tg = pd.read_csv(f, usecols=['t', 'tag']); dep = tg.tag.str.split('|').str[2].astype(float).to_numpy()
    x = x.reset_index(drop=True); tg = tg.assign(t=pd.to_datetime(tg.t), dep=dep).drop_duplicates('t')
    x = x.merge(tg[['t', 'dep']], left_on='tt', right_on='t', how='left')
    return x[x.dep >= depth].assign(key=f'DS@{sym}', pair=sym)[c]


ALL = ['EURUSD', 'USDJPY', 'XAUUSD', 'XAGUSD', 'US30', 'US500', 'JP225']
D7 = pd.concat([ds(s) for s in ALL]); D3 = pd.concat([ds(s) for s in ('USDJPY', 'XAUUSD', 'JP225')]); D6 = pd.concat([ds(s, 6.0) for s in ALL])
print({k: len(v) for k, v in dict(D7=D7, D3=D3, D6=D6).items()})
pfx.ev(base, keys4, pd.concat([CJ, M2]), label='候補（④ ドル円C絞る＋指数RSI2）')
pfx.ev(base, keys4, pd.concat([CJ, M2, D7]), label='＋右肩 7銘柄（押し4ATR+）')
pfx.ev(base, keys4, pd.concat([CJ, M2, D6]), label='＋右肩 7銘柄（押し6ATR+）')
pfx.ev(base, keys4, pd.concat([CJ, M2, D3]), label='＋右肩 ドル円・金・日経だけ（後から選んだ＝参考）')
# deep dive (2026-10-23): instruments chosen on the first half only, and one at a time
D4 = pd.concat([ds(s) for s in ('JP225', 'US30', 'USDJPY', 'XAUUSD')])
pfx.ev(base, keys4, pd.concat([CJ, M2, D4]), label='＋右肩 前半だけで選んだ4銘柄（日経・US30・ドル円・金）')
for s in ('USDJPY', 'XAUUSD', 'JP225', 'US30'):
    pfx.ev(base, keys4, pd.concat([CJ, M2, ds(s)]), label=f'＋右肩 {s} だけ')
pfx.ev(base, keys4, pd.concat([CJ, M2, ds('XAUUSD'), ds('JP225')]), label='＋右肩 金・日経')
