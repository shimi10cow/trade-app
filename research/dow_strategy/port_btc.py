"""BTC trend EA (S, buys only; with and without pyramiding K2) added to the adopted set (2026-10-24).
Settings chosen on BTC's first half (2017-21). Same-risk comparison and fixed 0.75 %; plus a swap estimate with XM's
current BTC long swap (-0.0703 % of the price per night, every night) over each trade's nights."""
import numpy as np, pandas as pd, pfx, port_ds2 as P2, port_ds_us500 as PU, new_summary as N
CS = P2.CS; S = CS.S
X = pd.concat([P2.X1, PU.U], ignore_index=True); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et); keys = list(X.key.unique())
R = f'{S}/ws_BTCUSD/research/dow_strategy/results/'


def btc(f, key, swap=False):
    x = N.load('BTCUSD', f).reset_index(drop=True)
    if swap:
        n = ((x.et.dt.normalize() - x.tt.dt.normalize()) / pd.Timedelta('1D')).clip(lower=0)
        x['R'] = x.R - 0.000703 * n / x.risk          # risk is in log units = share of price
    return x.assign(key=key, pair='BTCUSD')[['R', 'tt', 'et', 'key', 'pair']]


C = {'S 買い（ma_ma_buy_mt3_h1a2）': 'st2/S_ma_ma_buy_mt3_h1a2.csv', 'K2 S 買い＋買い増し（前半最良）': 'st2/K2_S_ma_prov_buy_mt3_h4a1.csv'}
pfx.ev(X, keys, label='採用（右肩 3 銘柄込み）')
for nm, f in C.items():
    for sw in (False, True):
        b = btc(f, 'BTC', sw); y = pd.concat([X, b], ignore_index=True)
        pfx.ev(y, keys, b, label=f'＋BTC {nm}{"（スワップ込み）" if sw else ""} {b.R.sum():+.0f}R')
        c, dd, yy, n = CS.fixed(y, 0.0075); print(f'    0.75%固定 年利 {c:.1%} 最大DD {dd:.1%}')
x = N.load('BTCUSD', 'st2/K2_S_ma_prov_buy_mt3_h4a1.csv')
print('K2 の持ち越し日数 中央', ((x.et - x.tt) / pd.Timedelta('1D')).median().round(1), '損切り幅 中央', f'{x.risk.median():.2%}')
