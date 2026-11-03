import sys, pickle, bisect, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition.pivots import atr
X = pd.read_pickle('full/current.pkl'); X = X[X.sym == 'USDJPY'].copy()
F = pickle.load(open('live_frames_USDJPY.pkl', 'rb'))
A4 = atr(F.h4); c4 = pd.Series(F.h4.c.to_numpy(float)); S1200 = c4.rolling(1200).mean().to_numpy(); C4 = list(F.C4)
def sd(t, s): k = bisect.bisect_right(C4, t) - 1; return s * (c4[k] - S1200[k]) / A4[k]
X['sdv'] = [sd(t, s) for t, s in zip(X.t, X.side)]
X['hour'] = X.t.dt.hour; X['h2'] = X.t >= '2016-01-01'
def t(r): return r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 2 else np.nan
for k in ('C@USDJPY', 'J2@USDJPY', 'P@USDJPY'):
    x = X[X.key == k]; print(f'== {k} n{len(x)} {x.R.mean():+.3f} t{t(x.R):.2f}  買い {x[x.side==1].R.mean():+.2f}({(x.side==1).sum()}) 売り {x[x.side==-1].R.mean():+.2f}({(x.side==-1).sum()})')
    print('   年:', x.groupby(x.t.dt.year).R.sum().round(1).to_dict())
    for col, bins in (('sdv', [-99, 0, 2, 4, 8, 99]), ('m20d', [-9, -0.9, 0, 1, 2, 9]), ('imp', [0, 3, 6, 10, 99]), ('op', [-9, 0, 1, 2.5, 9]), ('sl4', [-9, 0, 0.35, 0.7, 9]), ('h1sl', [-9, 0, 0.3, 0.7, 9]), ('hour', [-1, 6, 12, 18, 24])):
        g = x.groupby(pd.cut(x[col], bins), observed=True)
        print(f'   {col}: ' + ' | '.join(f'{iv}: n{len(v)} {v.R.mean():+.2f} ({v[~v.h2].R.mean():+.2f}/{v[v.h2].R.mean():+.2f})' for iv, v in g))
c = X[X.key == 'C@USDJPY']; j = X[X.key == 'J2@USDJPY']
ov = lambda a, b: [((b.t < r.exit_t) & (b.exit_t > r.t)).any() for r in a.itertuples()]
ovs = lambda a, b: [((b.t < r.exit_t) & (b.exit_t > r.t) & (b.side == r.side)).any() for r in a.itertuples()]
c = c.assign(ov=ov(c, j), ovs=ovs(c, j)); j = j.assign(ov=ov(j, c), ovs=ovs(j, c))
print(f'== 重なり: C が J2 と保有が重なる {c.ov.sum()}/{len(c)}（同じ向き {c.ovs.sum()}）、J2 が C と {j.ov.sum()}/{len(j)}（同じ向き {j.ovs.sum()}）')
print(f'   C: 重なる {c[c.ovs].R.mean():+.2f} / 重ならない {c[~c.ovs].R.mean():+.2f}   J2: 重なる {j[j.ovs].R.mean():+.2f} / 重ならない {j[~j.ovs].R.mean():+.2f}')
mc = c.groupby(c.exit_t.dt.to_period('M')).R.sum(); mj = j.groupby(j.exit_t.dt.to_period('M')).R.sum(); m = pd.concat([mc, mj], axis=1).fillna(0)
print(f'   月の相関 C×J2 {m.iloc[:,0].corr(m.iloc[:,1]):+.2f}')
X.to_pickle('full/jpy.pkl')
