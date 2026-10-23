"""Exit study for the right shoulder (ds_ea.py with DS_EXITS; H1 version, stop above the left shoulder, pullback >= 4 ATR H4).
Per exit: mean R / PF / win rate / hours held by half, for gold and Nikkei, and for all 7 instruments (to see if a choice
only works where we already looked)."""
import glob, os, numpy as np, pandas as pd
import new_summary as N
S = N.S
SYMS = ['EURUSD', 'USDJPY', 'XAUUSD', 'XAGUSD', 'US30', 'US500', 'JP225']


def rdir(sym):
    return '/home/user/trade-app/research/dow_strategy/results' if sym == 'EURUSD' else f'{S}/ws_{sym}/research/dow_strategy/results'


def load(sym, fn):
    f = f'{rdir(sym)}/ds/{fn}'
    d = pd.read_csv(f)
    if sym in N.COST:
        x = N.load(sym, f'ds/{fn}')
    else:
        x = pd.DataFrame(dict(tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), R=d.R, side=d.side, risk=d.risk))
        x = x[x.tt.dt.year >= 2005].copy(); x['half'] = np.where(x.tt.dt.year <= 2015, 1, 2)
    tg = pd.DataFrame(dict(t=pd.to_datetime(d.t), dep=d.tag.str.split('|').str[2].astype(float))).drop_duplicates('t')
    x = x.merge(tg, left_on='tt', right_on='t', how='left')
    return x[x.dep >= 4]


def pf(r): return r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())


rows = []
for sym in SYMS:
    for f in sorted(glob.glob(f'{rdir(sym)}/ds/DS_H1_left_*.csv')):
        ex = os.path.basename(f)[:-4].split('_', 3)[3]
        x = load(sym, os.path.basename(f)); x['hold'] = (x.et - x.tt) / pd.Timedelta('1h')
        for h in (1, 2):
            r = x[x.half == h]
            rows.append(dict(sym=sym, ex=ex, half=h, n=len(r), mean=r.R.mean(), PF=pf(r.R), win=(r.R > 0).mean(), sumR=r.R.sum(), hold=r.hold.median()))
D = pd.DataFrame(rows); D.to_pickle(f'{S}/feat/ds_exit_eval.pkl')
pd.set_option('display.width', 230)
for grp, syms in (('ゴールド・日経', ['XAUUSD', 'JP225']), ('7 銘柄', SYMS)):
    g = D[D.sym.isin(syms)].groupby(['ex', 'half']).apply(lambda d: pd.Series(dict(n=d.n.sum(), mean=d.sumR.sum() / d.n.sum(), sumR=d.sumR.sum()))).unstack('half').round(2)
    pos = D[D.sym.isin(syms)].pivot_table(index=['ex', 'sym'], columns='half', values='sumR')
    g['前後半とも黒字の銘柄'] = ((pos[1] > 0) & (pos[2] > 0)).groupby('ex').sum()
    print(f'\n== {grp}'); print(g.to_string())
print('\n== ゴールド・日経 銘柄別（平均R・PF・勝率・保有時間の中央値 h）')
print(D[D.sym.isin(['XAUUSD', 'JP225'])].pivot_table(index=['sym', 'ex'], columns='half', values=['mean', 'PF', 'win', 'hold']).round(2).to_string())
