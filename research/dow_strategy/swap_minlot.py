"""XM KIWAMI specs (snapshot 2026-10-24, uploads/xm_swap_specs_snapshot.csv) applied to the adopted EAs.
Swap: FX / gold / silver swap_mode 0 = disabled (no swap). Indices: swap_mode 3 (margin currency per lot per day),
triple on Friday; BTC: points per lot per day (charged every night incl. weekends).
Daily swap as a share of today's price (long / short):"""
import numpy as np, pandas as pd, pfx, port_ds2 as P2, new_summary as N
CS = P2.CS; S = CS.S
PX = {'US30': 52000, 'US500': 7670, 'JP225': 62500, 'XAUUSD': 4135, 'XAGUSD': 56.9, 'USDJPY': 158.5, 'EURUSD': 1.116, 'BTCUSD': 81800}
SWAP = {'US30': (-8.49, 1.27), 'US500': (-1.26, 0.19), 'JP225': (-4.81, -1.01), 'BTCUSD': (-57.54, -23.01)}   # per lot per day, lot = 1 unit
DAILY = {k: (a / PX[k], b / PX[k]) for k, (a, b) in SWAP.items()}
LOT = {'EURUSD': (1000, 'USD'), 'USDJPY': (1000, 'JPY_USDJPY'), 'XAUUSD': (1, 'USD'), 'XAGUSD': (50, 'USD'), 'US30': (0.1, 'USD'),
       'US500': (0.1, 'USD'), 'JP225': (0.1, 'JPY'), 'BTCUSD': (0.01, 'USD')}                                        # units at the minimum lot
R = f'{S}/ws_{{}}/research/dow_strategy/results/{{}}'


def nights(tt, et, triple_fri=True):
    d = pd.date_range(tt.normalize() + pd.Timedelta('1D'), et.normalize(), freq='D')
    if not triple_fri: return len(d)
    wd = d.dayofweek                               # rollover at broker midnight; the one into Saturday counts 3, weekend days none
    return int(((wd >= 1) & (wd <= 4)).sum() + 3 * (wd == 5).sum())


rows = []
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl')
for k in ('R@EURUSD', 'T2@EURUSD', 'L@EURUSD', 'A@EURUSD', 'C@EURUSD', 'J2@USDJPY', 'C@USDJPY', 'L2@XAUUSD', 'S@XAUUSD'):
    g = T[T.key == k]; w = g.risk if k.endswith('XAUUSD') else g.risk / g.entry      # gold workspace prices are logs
    rows.append(pd.DataFrame(dict(key=k, pair=g.pair, tt=pd.to_datetime(g.tt), et=pd.to_datetime(g.et), side=g.side, w=w)))
Q = pd.read_pickle(f'{S}/feat/q_best.pkl'); g = Q[Q.pair == 'XAUUSD']
rows.append(pd.DataFrame(dict(key='Q@XAUUSD', pair='XAUUSD', tt=pd.to_datetime(g.tt), et=pd.to_datetime(g.et), side=g.side, w=g.risk)))
for key, sym, f, tc, ec in (('T@US30', 'US30', 'regime2_T1t.csv', 'time', 'ExitTime'), ('Q@US30', 'US30', 'q/Q_1.0_24_ma_dow_ref_h1.csv', 't', 'exit_t'),
                            ('Q@XAGUSD', 'XAGUSD', 'q/Q_0.8_24_any_dow_ref_h4.csv', 't', 'exit_t'), ('M@US30', 'US30', 'rsi2/M_200_10_ma5_st.csv', 't', 'exit_t'),
                            ('M@US500', 'US500', 'rsi2/M_200_10_ma5_st.csv', 't', 'exit_t')):
    d = pd.read_csv(R.format(sym, f))
    rows.append(pd.DataFrame(dict(key=key, pair=sym, tt=pd.to_datetime(d[tc]), et=pd.to_datetime(d[ec]), side=d.side, w=d.risk)))
for sym in ('XAUUSD', 'JP225', 'US500'):
    d = pd.read_csv(R.format(sym, 'ds/DS_H1_left_tp2.csv')); d = d[d.tag.str.split('|').str[2].astype(float) >= 4]
    if sym == 'US500': d = d[d.side == 1]
    rows.append(pd.DataFrame(dict(key=f'DS@{sym}', pair=sym, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), side=d.side, w=d.risk)))
A = pd.concat(rows, ignore_index=True).dropna(subset=['tt', 'et'])
A['nights'] = [nights(a, b) for a, b in zip(A.tt, A.et)]
A['swapR'] = [(DAILY[p][0] if s == 1 else DAILY[p][1]) * n / w if p in DAILY else 0.0 for p, s, n, w in zip(A.pair, A.side, A.nights, A.w)]
units, cur = zip(*[LOT[p] for p in A.pair])
usd = PX['USDJPY']
A['minlot_jpy'] = [w * PX[p] * u * (usd if c == 'USD' else 1.0) for w, p, u, c in zip(A.w, A.pair, units, cur)]
A['minlot_jpy'] = np.where(A.pair == 'USDJPY', A.w * PX['USDJPY'] * 1000, A.minlot_jpy)
A.to_pickle(f'{S}/feat/swap_minlot.pkl')
pd.set_option('display.width', 230)
print('1 日のスワップ（今の価格に対する割合、買い／売り）:', {k: f'{a:+.4%} / {b:+.4%}' for k, (a, b) in DAILY.items()})
g = A.groupby('key').agg(回数=('w', 'size'), 持ち越し中央=('nights', 'median'), スワップ平均R=('swapR', 'mean'), スワップ合計R=('swapR', 'sum'),
                         損切り幅中央=('w', 'median'), 最小ロットのリスク中央=('minlot_jpy', 'median'),
                         超3000円=('minlot_jpy', lambda x: (x > 3000).mean()), 超4500円=('minlot_jpy', lambda x: (x > 4500).mean()))
g['損切り幅中央'] = (g['損切り幅中央'] * 100).round(2).astype(str) + '%'
print(g.round(3).to_string())
# portfolio with swap
X = P2.X1.copy(); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
x = N.load('US500', 'ds/DS_H1_left_tp2.csv').reset_index(drop=True)
d = pd.read_csv(R.format('US500', 'ds/DS_H1_left_tp2.csv'), usecols=['t', 'tag', 'side']).assign(t=lambda d: pd.to_datetime(d.t)).drop_duplicates('t')
d['dep'] = d.tag.str.split('|').str[2].astype(float); x = x.merge(d[['t', 'dep']], left_on='tt', right_on='t', how='left')
U = x[(x.dep >= 4) & (x.side == 1)].assign(key='DS@US500', pair='US500')[['R', 'tt', 'et', 'key', 'pair']]
X2 = pd.concat([X, U], ignore_index=True); X2['tt'] = pd.to_datetime(X2.tt); X2['et'] = pd.to_datetime(X2.et)
sw = A.set_index(['key', 'tt']).swapR; sw = sw[~sw.index.duplicated()]
X3 = X2.copy(); X3['R'] = X3.R + pd.Series(list(zip(X3.key, X3.tt))).map(lambda k: sw.get(k, 0.0)).to_numpy()
keys = list(X2.key.unique())
pfx.ev(X2, keys, label='採用＋US500右肩（スワップなし）')
pfx.ev(X3, keys, label='同じ（スワップ込み）')
for nm, Y in (('スワップなし', X2), ('スワップ込み', X3)):
    c, dd, y, n = CS.fixed(Y, 0.0075); print(f'{nm}: 0.75%固定 年利 {c:.1%} 最大DD {dd:.1%}')
print('\nスワップ込みの EA 別合計R（前後半）:')
X3['half'] = [1 if t.year <= {'US30': 2020, 'US500': 2021, 'JP225': 2021}.get(p, 2015) else 2 for t, p in zip(X3.tt, X3.pair)]
X2['half'] = X3.half
for k in ('T@US30', 'Q@US30', 'M@US30', 'M@US500', 'DS@JP225', 'DS@US500'):
    a = X2[X2.key == k].groupby('half').R.sum(); b = X3[X3.key == k].groupby('half').R.sum()
    print(f'  {k}: なし {a.round(1).to_dict()} → 込み {b.round(1).to_dict()}')
