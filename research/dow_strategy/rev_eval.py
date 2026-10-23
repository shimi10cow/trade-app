"""Evaluate rev_tl.py (counter-trend at strong H4 levels) across instruments, by half, with filters from the tag:
react (earlier reactions at the level), run (rise into it, ATR H1), h1d (H1 Dow running into the level = +1),
rsi1 (H1 RSI into the level, aligned: 100 - RSI for a buy), rsi15 (M15 RSI before the trigger, aligned)."""
import glob, os, sys, numpy as np, pandas as pd
import new_summary as N
S = N.S
SYMS = sys.argv[1:] or ['EURUSD', 'USDJPY', 'XAUUSD', 'XAGUSD', 'US30', 'US500', 'JP225']


def rdir(sym):
    return '/home/user/trade-app/research/dow_strategy/results' if sym == 'EURUSD' else f'{S}/ws_{sym}/research/dow_strategy/results'


def load(sym, f):
    if sym in N.COST: return N.load(sym, f)
    p = f'{rdir(sym)}/{f}'
    if not os.path.exists(p): return None
    d = pd.read_csv(p)
    if not len(d): return None
    x = pd.DataFrame(dict(tt=pd.to_datetime(d.t), R=d.R, side=d.side, risk=d.risk))
    x = x[(x.tt.dt.year >= 2005)]; x['half'] = np.where(x.tt.dt.year <= 2015, 1, 2); return x


rows = []
for sym in SYMS:
    for f in sorted(glob.glob(f'{rdir(sym)}/rev/RV_*.csv')):
        nm = os.path.basename(f)[3:-4]; x = load(sym, 'rev/' + os.path.basename(f))
        if x is None: continue
        tag = pd.read_csv(f, usecols=['t', 'tag']); tag['t'] = pd.to_datetime(tag.t)
        x = x.merge(tag, left_on='tt', right_on='t', how='left').drop_duplicates('tt')
        z = x.tag.str.split('|', expand=True).astype(float)
        x['react'], x['run'], x['h1d'], x['rsi1'], x['rsi15'] = z[0], z[1], z[2], z[3], z[4]
        x.loc[x.side == 1, 'rsi1'] = 100 - x.rsi1; x.loc[x.side == 1, 'rsi15'] = 100 - x.rsi15
        trig, buf, ex = nm.rsplit('_', 2)
        rows.append(x.assign(sym=sym, trig=trig, ex=ex))
A = pd.concat(rows, ignore_index=True)
A.to_pickle(f'{S}/feat/rev_eval.pkl')
FL = {'全部': A.R.notna(), '反発1回以上': A.react >= 1, '反発2回以上': A.react >= 2, '伸び4ATR超': A.run >= 4,
      'H1ダウが向かう': A.h1d == 1, 'H1 RSI 70超': A.rsi1 >= 70, 'M15 RSI 70超': A.rsi15 >= 70,
      '反発1+・伸び4+・H1向かう': (A.react >= 1) & (A.run >= 4) & (A.h1d == 1),
      '反発1+・H1 RSI70+': (A.react >= 1) & (A.rsi1 >= 70)}
pd.set_option('display.width', 250)


def pf(r): return r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())


out = []
for fn, m in FL.items():
    for (trig, ex), g in A[m].groupby(['trig', 'ex']):
        r1 = g[g.half == 1].R; r2 = g[g.half == 2].R
        nsym = sum(1 for _, h in g.groupby('sym') if h[h.half == 1].R.sum() > 0 and h[h.half == 2].R.sum() > 0)
        out.append(dict(filter=fn, trig=trig, ex=ex, n1=len(r1), m1=r1.mean(), PF1=pf(r1), n2=len(r2), m2=r2.mean(), PF2=pf(r2), both_pos_syms=nsym))
O = pd.DataFrame(out).round(2)
print('== 7 銘柄合計（平均R・PF、前半／後半）、both_pos_syms = 前後半とも黒字の銘柄数')
for fn in FL: print(f'\n-- {fn}'); print(O[O['filter'] == fn].drop(columns='filter').to_string(index=False))
O.to_csv(f'{S}/rev_eval.csv', index=False)
