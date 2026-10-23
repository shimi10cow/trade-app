"""Gold: the user's H4 marks (2013 / 2019: B = trend start with side, N = pullback, R = range) vs the H4 Dow states and the
gold EA trades (2026-10-23). Run inside the XAUUSD workspace.
 (1) user's trend state over time vs H4 major / provisional Dow state (agreement, number of switches)
 (2) gold EA trades by the user's state at entry: same side / opposite / range
 (3) 20 years: trades by H4 MAJOR state (戻り高値/押し安値 broken = confirmed) vs only the provisional state agreeing"""
import sys, json, glob
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
M = pd.DataFrame([json.load(open(f)) for f in glob.glob(f'{S}/gold_marks/pbmarks/*.json')])
M['tm'] = pd.to_datetime(M.t, unit='s'); M = M.sort_values('tm')
st = []; cur = 0
for x in M.itertuples():
    if x.kind == 'B': cur = int(x.side)
    elif x.kind == 'R': cur = 0
    st.append((x.tm, cur))
U = pd.Series([s for _, s in st], index=pd.DatetimeIndex([t for t, _ in st]))
C4 = pd.DatetimeIndex(B.C4); h4t = pd.DatetimeIndex(pd.to_datetime(B.h4.t))
maj = np.array([{'up': 1, 'down': -1}.get(b[0], 0) for b in B.R4['bars']]); prv = np.array([{'up': 1, 'down': -1}.get(b[0], 0) for b in B.R4['prov_bars']])
def at_arr(arr, t):
    k = C4.searchsorted(t, 'right') - 1
    return arr[np.clip(k, 0, len(arr) - 1)]
def user_at(t):
    i = U.index.searchsorted(t, 'right') - 1
    return np.where(i >= 0, U.to_numpy()[np.maximum(i, 0)], np.nan)
# (1) agreement on H4 bars inside the marked periods
for y in (2013, 2019):
    sel = (h4t.year == y); tt = C4[sel]; u = user_at(tt); m4 = at_arr(maj, tt); p4 = at_arr(prv, tt)
    ok = u != 0
    sw = lambda a: int((np.diff(a) != 0).sum())
    print(f'{y}: H4 足 {sel.sum()}、あなたの向きが「買い」{(u == 1).mean():.0%}・「売り」{(u == -1).mean():.0%}・「レンジ」{(u == 0).mean():.0%}'
          f' | レンジ以外で 本ダウと一致 {(m4[ok] == u[ok]).mean():.0%}、仮ダウと一致 {(p4[ok] == u[ok]).mean():.0%}'
          f' | 向きの切り替え回数 あなた {sw(u)}・本ダウ {sw(m4)}・仮ダウ {sw(p4)}')
# (2)+(3) EA trades
R = B.HERE / 'results'
FILES = {'S': 'st2/S_ma_prov_buy_mt3_h1a1.csv', 'Q': 'q/Q_0.8_24_ma_now_ref_h1.csv', 'L2': 'tl_N2_room1.csv', 'C': 'step2/cl15_md4tri.csv',
         'J3': 'turn/j3_h41_s0_h1prot.csv', 'P': 'pb/P4_maj0_rs0.5.csv', 'DIP': 'idip/D_d1ma_ma75_dow_h4.csv', 'U': 'turtle/U_20_10_2_buy.csv'}
rows = []
for k, f in FILES.items():
    if not (R / f).exists(): continue
    d = pd.read_csv(R / f); t = pd.to_datetime(d.t); r = d.R - 1.3e-4 / d.risk
    rows.append(pd.DataFrame(dict(ea=k, t=t, side=d.side, R=r, u=user_at(t), maj=at_arr(maj, t), prv=at_arr(prv, t))))
X = pd.concat(rows, ignore_index=True); X['half'] = np.where(X.t.dt.year <= 2015, 1, 2)
Y = X[X.t.dt.year.isin([2013, 2019])].dropna(subset=['u'])
Y['あなた'] = np.where(Y.u == 0, 'レンジ', np.where(Y.u == Y.side, '同じ向き', '逆向き'))
print('\n### 2013・2019 の EA トレード：あなたの向きと比べて（回数・平均R・合計R）')
print(Y.groupby(['あなた']).R.agg(['count', 'mean', 'sum']).round(2).to_string())
print(Y.groupby(['ea', 'あなた']).R.agg(['count', 'sum']).round(1).unstack('あなた').to_string())
X['本ダウ'] = np.where(X.maj == X.side, '同じ', np.where(X.maj == -X.side, '逆', 'なし'))
X['仮ダウ'] = np.where(X.prv == X.side, '同じ', '逆/なし')
print('\n### 20 年：H4 の本ダウ（戻り高値・押し安値を抜けて確定）の向き × 仮ダウ（平均R 前半/後半・回数）')
print(X.groupby(['本ダウ', '仮ダウ', 'half']).R.agg(['count', 'mean']).unstack('half').round(3).to_string())
print('\n### EA ごと：本ダウと同じ向きだけ vs それ以外（合計R 前半/後半）')
g = X.assign(m=X.本ダウ == '同じ').groupby(['ea', 'm', 'half']).R.sum().unstack(['m', 'half']).round(1); print(g.to_string())
X.to_pickle(f'{S}/feat/gold_marks_trades.pkl')
