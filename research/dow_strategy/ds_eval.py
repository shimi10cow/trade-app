"""Evaluate ds_ea.py (double top / bottom right shoulder) across instruments by half, with filters from the tag:
res (left shoulder on an older H4 swing level), retr (how far the right shoulder came back, share of H-L), depth ((H-L) / ATR H4)."""
import glob, os, sys, numpy as np, pandas as pd
import new_summary as N
S = N.S
SYMS = sys.argv[1:] or ['EURUSD', 'USDJPY', 'XAUUSD', 'XAGUSD', 'US30', 'US500', 'JP225']


def rdir(sym):
    return '/home/user/trade-app/research/dow_strategy/results' if sym == 'EURUSD' else f'{S}/ws_{sym}/research/dow_strategy/results'


def load(sym, f):
    if sym in N.COST: return N.load(sym, f)
    d = pd.read_csv(f'{rdir(sym)}/{f}')
    if not len(d): return None
    x = pd.DataFrame(dict(tt=pd.to_datetime(d.t), R=d.R, side=d.side, risk=d.risk))
    x = x[(x.tt.dt.year >= 2005)].copy(); x['half'] = np.where(x.tt.dt.year <= 2015, 1, 2); return x


def pf(r): return r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())


rows = []
for sym in SYMS:
    for f in sorted(glob.glob(f'{rdir(sym)}/ds/DS_*.csv')):
        x = load(sym, 'ds/' + os.path.basename(f))
        if x is None: continue
        tag = pd.read_csv(f, usecols=['t', 'tag']); tag['t'] = pd.to_datetime(tag.t)
        x = x.merge(tag, left_on='tt', right_on='t', how='left').drop_duplicates('tt')
        z = x.tag.str.split('|', expand=True)
        x['retr'], x['depth'], x['res'], x['hrs'] = z[1].astype(float), z[2].astype(float), z[3].astype(int), z[4].astype(float)
        _, tf, stop, ex = os.path.basename(f)[:-4].split('_')
        rows.append(x.assign(sym=sym, tf=tf, stop=stop, ex=ex))
A = pd.concat(rows, ignore_index=True); A.to_pickle(f'{S}/feat/ds_eval.pkl')
FL = {'全部': A.R.notna(), '左肩が過去の抵抗': A.res == 1, '戻り 50%以上': A.retr >= 0.5, '戻り 62%以上': A.retr >= 0.62,
      '押し 4ATR(H4)以上': A.depth >= 4, '抵抗 & 戻り50%+': (A.res == 1) & (A.retr >= 0.5), '抵抗 & 押し4+': (A.res == 1) & (A.depth >= 4)}
out = []
for fn, m in FL.items():
    for (tf, stop, ex), g in A[m].groupby(['tf', 'stop', 'ex']):
        r1 = g[g.half == 1].R; r2 = g[g.half == 2].R
        nsym = sum(1 for _, h in g.groupby('sym') if h[h.half == 1].R.sum() > 0 and h[h.half == 2].R.sum() > 0)
        out.append(dict(filter=fn, tf=tf, stop=stop, ex=ex, n1=len(r1), m1=r1.mean(), PF1=pf(r1), n2=len(r2), m2=r2.mean(), PF2=pf(r2),
                        both_pos_syms=nsym, top5=g.R.nlargest(5).sum() / g.R.sum() if g.R.sum() > 0 else np.nan))
O = pd.DataFrame(out).round(2); O.to_csv(f'{S}/ds_eval.csv', index=False)
pd.set_option('display.width', 240)
for fn in FL: print(f'\n-- {fn}'); print(O[O['filter'] == fn].drop(columns='filter').to_string(index=False))
