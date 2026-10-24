"""BTC S buys without weekend entries (user 2026-10-24: no BTC entries on Saturday / Sunday). Trades entered on a broker
Saturday or Sunday are dropped (positions opened on weekdays may still be held over the weekend). With swap estimate."""
import numpy as np, pandas as pd, pfx, port_ds2 as P2, port_ds_us500 as PU, new_summary as N
CS = P2.CS
X = pd.concat([P2.X1, PU.U], ignore_index=True); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et); keys = list(X.key.unique())
x = N.load('BTCUSD', 'st2/S_ma_ma_buy_mt3_h1a2.csv').reset_index(drop=True)
n = ((x.et.dt.normalize() - x.tt.dt.normalize()) / pd.Timedelta('1D')).clip(lower=0); x['R'] = x.R - 0.000703 * n / x.risk
x['wk'] = x.tt.dt.dayofweek >= 5
print('週末エントリー', int(x.wk.sum()), '/', len(x), '回')
print(x.groupby(['wk', 'half']).R.agg(['size', 'mean', 'sum']).round(2).unstack('half').to_string())
for nm, b in (('全部', x), ('平日だけ', x[~x.wk])):
    b = b.assign(key='BTC', pair='BTCUSD')[['R', 'tt', 'et', 'key', 'pair']]
    a1 = b[b.tt.dt.year <= 2021].R; a2 = b[b.tt.dt.year > 2021].R
    print(f'{nm}: 前半 {len(a1)}回 {a1.sum():+.0f}R PF{N.pf(a1):.2f} / 後半 {len(a2)}回 {a2.sum():+.0f}R PF{N.pf(a2):.2f} 上位5回 {b.R.nlargest(5).sum() / b.R.sum():.0%}')
    y = pd.concat([X, b], ignore_index=True); pfx.ev(y, keys, b, label=f'＋BTC S 買い {nm}（スワップ込み）')
    c, dd, yy, k = CS.fixed(y, 0.0075); print(f'    0.75%固定 年利 {c:.1%} 最大DD {dd:.1%}')
