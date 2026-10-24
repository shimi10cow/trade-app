"""Late in the trend: does following still pay? (user, 2026-10-23). Every EA trade (trade_pool) gets the H4 / H1 trend stage
(trend_stage.py) of the last bar closed before the entry. Trades WITH the H4 (H1) major trend are split by
age (bars since the trend began), run (move from the start, ATR), push (number of new highs/lows so far), dev (distance
from SMA75 in ATR, + = stretched in the trend direction). Mean R by half, adopted EAs and all EAs; then per instrument."""
import glob, numpy as np, pandas as pd
import trade_pool as TP
S = TP.S
X = TP.load_all(); rows = []
for f in sorted(glob.glob(f'{S}/feat/stage_*.pkl')):
    sym = f.split('stage_')[1][:-4]; st = pd.read_pickle(f); g = X[X.pair == sym].copy()
    if not len(g): continue
    for tf, d in st.items():
        k = np.searchsorted(d.t.to_numpy(), g.tt.to_numpy(), 'right') - 1; ok = k >= 0; k = np.maximum(k, 0)
        for c in ('age', 'run', 'push', 'dev'): g[f'{tf}_{c}'] = np.where(ok, d[c].to_numpy()[k], np.nan)
        g[f'{tf}_rel'] = np.where(ok, d.trend.to_numpy()[k] * g.side.to_numpy(), 0)
    rows.append(g)
F = pd.concat(rows, ignore_index=True); F.to_pickle(f'{S}/feat/late_eval.pkl')
BINS = {'H4': dict(age=[-1, 30, 60, 120, 1e9], run=[-1, 3, 6, 10, 1e9], push=[-1, 1, 2, 3, 99], dev=[-99, 0, 2, 4, 99]),
        'H1': dict(age=[-1, 30, 120, 300, 1e9], run=[-1, 3, 6, 10, 1e9], push=[-1, 1, 2, 3, 99], dev=[-99, 0, 2, 4, 99])}
pd.set_option('display.width', 220)
for tf in ('H4', 'H1'):
    print(f'\n################ {tf} トレンドとの関係（全トレード）')
    print(F.groupby([F.adopt.map({True: '採用', False: '不採用'}), f'{tf}_rel', 'half']).R.agg(['size', 'mean']).unstack('half').round(3).to_string())
    W = F[F[f'{tf}_rel'] == 1]
    for c, b in BINS[tf].items():
        print(f'\n== {tf} トレンドに沿うトレード：{c}')
        for nm, sub in (('採用', W[W.adopt]), ('全EA', W)):
            t = sub.groupby([pd.cut(sub[f'{tf}_{c}'], b), 'half'], observed=True).R.agg(['size', 'mean']).unstack('half').round(3)
            print(f'-- {nm}'); print(t.to_string())
# late = big run or many pushes on H4
W = F[F.H4_rel == 1].copy(); W['late'] = (W.H4_run >= 10) | (W.H4_push >= 4)
print('\n################ H4 後半（伸び 10ATR 以上 または 更新 4 回以上）vs それ以外：銘柄別（採用EA / 全EA）')
for nm, sub in (('採用', W[W.adopt]), ('全EA', W)):
    t = sub.groupby(['pair', 'late', 'half']).R.agg(['size', 'mean']).unstack('half').round(2)
    print(f'-- {nm}'); print(t.to_string())
print('\n-- EA 別（採用、H4 後半）'); print(W[W.adopt].groupby(['key', 'late', 'half']).R.agg(['size', 'mean']).unstack('half').round(2).to_string())
