"""Right shoulder (ds_ea.py) deep dive for USDJPY / XAUUSD / JP225 (user, 2026-10-23: is the gain real, how many trades,
is it one big trade?). Base = H1 trend break, stop above the left shoulder, 2R target, pullback >= 4 ATR(H4).
  1. trades per year, win rate, mean R, PF, by half; without the top 5 trades
  2. R by year (share of positive years)
  3. buys vs sells
  4. neighbouring settings: depth 3 / 4 / 5 / 6, other exits (H1 trail, neck), shoulder stop, H4 version
  5. portfolio: instruments chosen on the FIRST half only (mean R > 0 there), then judged on the second half"""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/ds_eval.pkl')
SY = ['USDJPY', 'XAUUSD', 'JP225']
pd.set_option('display.width', 220)


def pf(r): return r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())


def summ(g):
    r = g.R; yrs = max(1, g.tt.dt.year.nunique())
    return pd.Series(dict(n=len(r), per_year=len(r) / yrs, win=(r > 0).mean(), mean=r.mean(), PF=pf(r), sumR=r.sum(),
                          top5=r.nlargest(5).sum(), sum_wo_top5=r.sum() - r.nlargest(5).sum(), maxR=r.max()))


base = A[(A.tf == 'H1') & (A.stop == 'left') & (A.ex == 'tp2') & (A.depth >= 4)]
print('== 1. 基本（H1・左肩の上に損切り・2R・押し4ATR以上）')
print(base[base.sym.isin(SY)].groupby(['sym', 'half']).apply(summ).round(2).to_string())
print('\n3 銘柄合計'); print(base[base.sym.isin(SY)].groupby('half').apply(summ).round(2).to_string())
print('\n== 2. 年ごとの合計R')
y = base[base.sym.isin(SY)].assign(year=lambda d: d.tt.dt.year).pivot_table(index='year', columns='sym', values='R', aggfunc='sum').round(1)
y['3銘柄'] = y.sum(axis=1); print(y.to_string()); print('プラスの年の割合', (y > 0).mean().round(2).to_dict())
print('\n== 3. 買い／売り')
print(base[base.sym.isin(SY)].groupby(['sym', 'side', 'half']).R.agg(['size', 'mean']).unstack('half').round(2).to_string())
print('\n== 4. 近い設定（平均R 前半／後半）')
rows = []
for sym in SY:
    for (tf, stop, ex), g in A[A.sym == sym].groupby(['tf', 'stop', 'ex']):
        for d in (3, 4, 5, 6):
            h = g[g.depth >= d]
            rows.append(dict(sym=sym, tf=tf, stop=stop, ex=ex, depth=d, n1=(h.half == 1).sum(), m1=h[h.half == 1].R.mean(), n2=(h.half == 2).sum(), m2=h[h.half == 2].R.mean()))
G = pd.DataFrame(rows).round(2)
print(G.pivot_table(index=['tf', 'stop', 'ex', 'depth'], columns='sym', values=['m1', 'm2']).round(2).to_string())
both = G[(G.m1 > 0) & (G.m2 > 0)]
print('\n前後半ともプラスの設定数（全 48 設定のうち）:', both.groupby('sym').size().to_dict())
print('\n== 5. 前半だけで銘柄を選ぶ（押し4ATR+・H1・左肩・2R の前半平均R > 0）')
fh = base[base.half == 1].groupby('sym').R.mean().round(2); print(fh.to_dict()); print('選ばれる銘柄:', list(fh[fh > 0].index))
