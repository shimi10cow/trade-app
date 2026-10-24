"""Calendar ideas on the portfolio (cal_study.py findings), same-risk comparison against the adopted set (incl. right shoulder):
  gold Friday : buy gold at Thursday's close, sell at Friday's close (gold Friday +0.10/+0.08 ATR, t 3.6/2.5)
  index Monday: buy US30 / US500 / JP225 at Friday's close, sell at Monday's close (2nd half t 3-4, 1st half t ~1)
  TOM         : buy gold / US500 3 trading days before the month end, sell at the 3rd trading day's close
  month start x1.5 : adopted EA trades entered in the first 3 trading days of a month at 1.5x risk
R of the calendar trades = return / (2 x ATR(D1)) minus cost (no stop; a 2 ATR move = 1R)."""
import numpy as np, pandas as pd, pfx, port_ds2 as P2
S = P2.CS.S
A = pd.read_pickle(f'{S}/feat/cal_daily.pkl')
COST = {'XAUUSD': 6e-5, 'US30': 1.5e-4, 'US500': 1.5e-4, 'JP225': 3e-4}
c = ['R', 'tt', 'et', 'key', 'pair']


def hold_day(sym, wd, key):
    D = A[A.sym == sym]; out = []
    idx = D.index
    for i in range(1, len(D)):
        if idx[i].dayofweek != wd: continue
        r = D.c.iloc[i] - D.c.iloc[i - 1] - COST[sym]
        out.append(dict(R=r / (2 * D.atr.iloc[i]), tt=idx[i - 1] + pd.Timedelta('23h'), et=idx[i] + pd.Timedelta('23h'), key=key, pair=sym))
    return pd.DataFrame(out)


def tom(sym, key):
    D = A[A.sym == sym]; ym = D.index.to_period('M'); out = []
    for p in ym.unique():
        g = D[ym == p]; nx = D[ym == p + 1]; e3 = g[g.neg == 3]
        if not len(e3) or len(nx) < 3: continue
        r = nx.c.iloc[2] - e3.c.iloc[0] - COST[sym]
        out.append(dict(R=r / (2 * e3.atr.iloc[0]), tt=e3.index[0] + pd.Timedelta('23h'), et=nx.index[2] + pd.Timedelta('23h'), key=key, pair=sym))
    return pd.DataFrame(out)


X1 = P2.X1.copy(); keys = list(X1.key.unique())
GF = hold_day('XAUUSD', 4, 'FRI@XAUUSD')
IM = pd.concat([hold_day(s, 0, f'MON@{s}') for s in ('US30', 'US500', 'JP225')])
TM = pd.concat([tom('XAUUSD', 'TOM@XAUUSD'), tom('US500', 'TOM@US500')])
for nm, d in (('金の金曜', GF), ('指数の月曜', IM), ('月末月初', TM)):
    print(nm, d.groupby(d.tt.dt.year <= 2015).R.agg(['size', 'mean', 'sum']).round(3).to_dict('index'))
pfx.ev(X1, keys, label='採用（右肩込み）')
pfx.ev(X1, keys, GF, label='＋金の金曜')
pfx.ev(X1, keys, IM, label='＋指数の月曜')
pfx.ev(X1, keys, TM, label='＋月末月初（金・US500）')
# month start x1.5 for the EA trades
pos = []
for sym, g in X1.groupby('pair'):
    D = A[A.sym == sym]; k = np.clip(D.index.searchsorted(pd.to_datetime(g.tt).dt.normalize()), 0, len(D) - 1)
    pos.append(pd.Series(D.pos.to_numpy()[k] <= 3, index=g.index))
ms = pd.concat(pos).reindex(X1.index).fillna(False).astype(bool)
X2 = X1.copy(); X2.loc[ms, 'R'] *= 1.5
print('月初 3 日のトレード', int(ms.sum()), '/', len(X1))
pfx.ev(X2, keys, label='月初 3 日のトレードを 1.5 倍')
