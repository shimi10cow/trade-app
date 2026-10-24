"""Gold block re-mix (2026-10-23): keep the total gold weight about the same as combo ④ (S 0.5 + Q 0.5 + L2 1.0 = 2.0)
and swap in the gold-specific logics found this cycle. Same-risk bootstrap, gold has 20 years so the usual halves apply."""
import pandas as pd, pfx, combo_stable as CS, new_summary as N
S = N.S; W = S + '/ws_XAUUSD/research/dow_strategy/results'
def g(f, key, w):
    d = pd.read_csv(f'{W}/{f}'); return pd.DataFrame(dict(R=(d.R - 1.3e-4 / d.risk) * w, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), key=key, pair='XAUUSD'))
keys4 = CS.P['④ ③＋US30（T・Q）']; base = CS.mk(keys4); base['tt'] = pd.to_datetime(base.tt); base['et'] = pd.to_datetime(base.et)
nog = [k for k in keys4 if not k.endswith('XAUUSD')]; b0 = base[~base.key.str.endswith('XAUUSD')]
gold4 = base[base.key.str.endswith('XAUUSD')]
L2 = gold4[gold4.key == 'L2@XAUUSD']; Sx = gold4[gold4.key == 'S@XAUUSD']; Qx = gold4[gold4.key == 'Q@XAUUSD']
DIP = 'idip/D_d1ma_ma75_dow_h4.csv'; TUR = 'turtle/U_20_10_2_buy.csv'; KS = 'st2/K2_S_ma_prov_buy_mt3_h4a1.csv'
SETS = {'④ 今の金（S½・Q½・L2）': [Sx, Qx, L2],
        '金なし': [],
        'L2・Q½・押し目½': [L2, Qx, g(DIP, 'DIP@XAUUSD', 0.5)],
        'L2・Q½・ブレイク½': [L2, Qx, g(TUR, 'U@XAUUSD', 0.5)],
        'L2・Q½・買い増しS½': [L2, Qx, g(KS, 'S@XAUUSD', 0.5)],
        '6種を1/3ずつ（S・Q・L2・押し目・ブレイク・買い増しS）': [Sx.assign(R=Sx.R * 2 / 3), Qx.assign(R=Qx.R * 2 / 3), L2.assign(R=L2.R / 3),
                                                       g(DIP, 'DIP@XAUUSD', 1 / 3), g(TUR, 'U@XAUUSD', 1 / 3), g(KS, 'K@XAUUSD', 1 / 3)]}
for lab, parts in SETS.items():
    ex = pd.concat(parts) if parts else None
    pfx.ev(b0, nog, ex, label=lab)
