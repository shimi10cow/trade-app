"""Combo ④ with the instrument-specific candidates (2026-10-23 cycle): gold S variants (H4 trail, pyramiding),
gold dip-buy (idx_dip, first-half best), RSI(2) dip-buy on US30 / US500 (classic setting, not chosen) and gold."""
import numpy as np, pandas as pd, pfx, combo_stable as CS, new_summary as N
S = N.S; W = S + '/ws_XAUUSD/research/dow_strategy/results'
def gold(f, key, w=1.0):
    d = pd.read_csv(f'{W}/{f}'); R = (d.R - 1.3e-4 / d.risk) * w
    return pd.DataFrame(dict(R=R, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), key=key, pair='XAUUSD'))
def new(sym, f, key):
    x = N.load(sym, f); return pd.DataFrame(dict(R=x.R, tt=x.tt, et=x.et, key=key, pair=sym))
keys4 = CS.P['④ ③＋US30（T・Q）']; base = CS.mk(keys4); base['tt'] = pd.to_datetime(base.tt); base['et'] = pd.to_datetime(base.et)
noS = [k for k in keys4 if k != 'S@XAUUSD']; b2 = base[base.key != 'S@XAUUSD']
cols = ['R', 'tt', 'et', 'key', 'pair']
pfx.ev(base, keys4, label='④ 基準（金S半分）')
for f, lab in (('st2/K1_S_ma_prov_buy_mt3_h4a1.csv', '金S→H4決済'), ('st2/K2_S_ma_prov_buy_mt3_h1a1.csv', '金S→買い増し2本'),
               ('st2/K2_S_ma_prov_buy_mt3_h4a1.csv', '金S→買い増し2本＋H4決済')):
    pfx.ev(b2, noS, gold(f, 'S@XAUUSD', 0.5), label=f'④ {lab}（半分）')
pfx.ev(base, keys4, gold('idip/D_d1ma_ma75_dow_h4.csv', 'DIP@XAUUSD'), label='④＋金 押し目買い')
pfx.ev(base, keys4, gold('rsi2/M_200_10_ma5_st.csv', 'M@XAUUSD'), label='④＋金 RSI2')
r2 = pd.concat([new('US30', 'rsi2/M_200_10_ma5_st.csv', 'M@US30'), new('US500', 'rsi2/M_200_10_ma5_st.csv', 'M@US500')])
pfx.ev(base, keys4, r2, label='④＋US30・US500 RSI2')
allc = pd.concat([gold('idip/D_d1ma_ma75_dow_h4.csv', 'DIP@XAUUSD'), r2])
pfx.ev(b2, noS, pd.concat([gold('st2/K2_S_ma_prov_buy_mt3_h4a1.csv', 'S@XAUUSD', 0.5), allc]), label='④ 全部入り')
