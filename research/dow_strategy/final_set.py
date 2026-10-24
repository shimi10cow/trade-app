"""Final adopted set (2026-10-24) as one trade table, with every correction applied. Writes feat/final_trades.pkl.
Members: combo ④ base (EURUSD R/T2/L/A/C, USDJPY C filtered / J2, gold L2 / S½ / Q½, silver Q, US30 T / Q), index RSI(2) (US30,
US500), right shoulder (JP225 left-stop 2R both sides, US500 left-stop 2R buys, gold right-shoulder-stop H1-trail buys),
BTC S buys (weekday entries only).
Corrections:
  swap     : XM KIWAMI today's swap (indices per night with Friday x3, BTC every night; FX / metals none) - swap_minlot.py
  entrybar : engines that skipped the entry bar (ea_core / tl_ea / retest_ea / dow_turn_ea): if the entry bar's range already
             reached the initial stop, the trade becomes a full loss (-1R - 0.05R cost); R/T2/T (engine_m15) and RSI(2) unaffected
  calendar : gold-Friday buys and the first 3 trading days of the month x1.5 (cal_size.py)
Columns: key, pair, tt, et, side, w (stop width as a share of price), R0 (as before), R (final), swapR, ebhit, mult, wt (half weight)."""
import numpy as np, pandas as pd, port_ds2 as P2, port_ds_us500 as PU, new_summary as N
CS = P2.CS; S = CS.S
RS = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad/ws_{}/research/dow_strategy/results/{}'
X = pd.concat([P2.X1[P2.X1.key != 'DS@XAUUSD'], PU.U], ignore_index=True)
# gold right shoulder: stop above the right shoulder, buys, H1 trail
d = pd.read_csv(RS.format('XAUUSD', 'ds/DS_H1_shoulder_h1.csv')); d = d[(d.tag.str.split('|').str[2].astype(float) >= 4) & (d.side == 1)]
G = pd.DataFrame(dict(R=d.R - 1.3e-4 / d.risk, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), key='DS@XAUUSD', pair='XAUUSD', side=1, w=d.risk))
# BTC S buys, weekday entries
b = N.load('BTCUSD', 'st2/S_ma_ma_buy_mt3_h1a2.csv').reset_index(drop=True); b = b[b.tt.dt.dayofweek < 5]
B = pd.DataFrame(dict(R=b.R, tt=b.tt, et=b.et, key='S@BTCUSD', pair='BTCUSD', side=1, w=b.risk))
X = pd.concat([X, G, B], ignore_index=True); X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)
X['wt'] = np.where(X.key.isin(['S@XAUUSD', 'Q@XAUUSD']), 0.5, 1.0)
# side / stop width for the rest from swap_minlot's table (raw trade files)
A = pd.read_pickle(f'{S}/feat/swap_minlot.pkl').drop_duplicates(['key', 'tt']).set_index(['key', 'tt'])
idx = pd.MultiIndex.from_arrays([X.key, X.tt])
X['side'] = X.side.fillna(pd.Series(A.side.reindex(idx).to_numpy(), index=X.index))
X['w'] = X.w.fillna(pd.Series(A.w.reindex(idx).to_numpy(), index=X.index))
X['R0'] = X.R
# swap
DAILY = {'US30': (-8.49 / 52000, 1.27 / 52000), 'US500': (-1.26 / 7670, 0.19 / 7670), 'JP225': (-4.81 / 62500, -1.01 / 62500), 'BTCUSD': (-57.54 / 81800, -23.01 / 81800)}


def nights(tt, et, btc):
    dd = pd.date_range(tt.normalize() + pd.Timedelta('1D'), et.normalize(), freq='D')
    if btc: return len(dd)
    wd = dd.dayofweek; return int(((wd >= 1) & (wd <= 4)).sum() + 3 * (wd == 5).sum())


X['swapR'] = [(DAILY[p][0] if s == 1 else DAILY[p][1]) * nights(a, e, p == 'BTCUSD') / w * wt if p in DAILY and np.isfinite(w) else 0.0
              for p, s, a, e, w, wt in zip(X.pair, X.side, X.tt, X.et, X.w, X.wt)]
# entry-bar stop check
AFFECTED = {'L@EURUSD', 'A@EURUSD', 'C@EURUSD', 'C@USDJPY', 'J2@USDJPY', 'L2@XAUUSD', 'S@XAUUSD', 'Q@XAUUSD', 'Q@XAGUSD', 'Q@US30',
            'DS@JP225', 'DS@US500', 'DS@XAUUSD', 'S@BTCUSD'}
SRC = {'EURUSD': (f'{S}/EURUSD_M15_long_broker.csv', False), 'USDJPY': (f'{S}/ws_USDJPY/M15_broker.csv', False)}
X['ebhit'] = False
for sym, g in X[X.key.isin(AFFECTED)].groupby('pair'):
    f, lg = SRC.get(sym, (f'{S}/ws_{sym}/M15_broker.csv', True))
    m = pd.read_csv(f, parse_dates=['time']).set_index('time'); m = m[~m.index.duplicated()]
    o, h, l = (m[c].reindex(g.tt).to_numpy() for c in ('open', 'high', 'low'))
    adv = np.where(g.side == 1, (o - l) if lg else 1 - l / o, (h - o) if lg else h / o - 1)
    X.loc[g.index, 'ebhit'] = np.nan_to_num(adv) >= g.w.to_numpy()
X['R'] = np.where(X.ebhit, -1.05 * X.wt, X.R0) + X.swapR
# calendar multipliers
CAL = pd.read_pickle(f'{S}/feat/cal_daily.pkl')
pos = np.full(len(X), 99)
for sym, g in X.groupby('pair'):
    D = CAL[CAL.sym == sym] if sym in set(CAL.sym) else CAL[CAL.sym == 'EURUSD']
    k = np.clip(D.index.searchsorted(g.tt.dt.normalize()), 0, len(D) - 1); pos[g.index] = D.pos.to_numpy()[k]
X['mult'] = np.where(((X.pair == 'XAUUSD') & (X.side == 1) & (X.tt.dt.dayofweek == 4)) | (pos <= 3), 1.5, 1.0)
X['Rm'] = X.R * X.mult
X['half'] = [1 if t.year <= {'US30': 2020, 'US500': 2021, 'JP225': 2021, 'BTCUSD': 2021}.get(p, 2015) else 2 for t, p in zip(X.tt, X.pair)]
X.to_pickle(f'{S}/feat/final_trades.pkl')
if __name__ == '__main__':
    pd.set_option('display.width', 220)
    g = X.groupby('key').agg(回数=('R', 'size'), 補正前=('R0', 'sum'), スワップ=('swapR', 'sum'), 入った足で損切り=('ebhit', 'sum'), 補正後=('R', 'sum'), 倍率込み=('Rm', 'sum'),
                             幅の欠け=('w', lambda x: x.isna().sum()))
    print(g.round(1).to_string()); print('合計', g[['補正前', 'スワップ', '補正後', '倍率込み']].sum().round(1).to_dict())
