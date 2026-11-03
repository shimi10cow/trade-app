import sys, pickle, bisect, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition.pivots import atr
X = pd.read_pickle('full/current.pkl'); q = X[X.key == 'Q@US30'].copy()
F = pickle.load(open('live_frames_US30.pkl', 'rb'))
A4 = atr(F.h4); c4 = pd.Series(F.h4.c.to_numpy(float)); S1200 = c4.rolling(1200).mean().to_numpy(); C4 = list(F.C4)
h1 = F.h1; C1 = list(F.C1); A1 = F.A1; H, L, Cc = h1.h.to_numpy(), h1.l.to_numpy(), h1.c.to_numpy()
S200 = pd.Series(Cc).rolling(200).mean().to_numpy()
def feats(t, s):
    k = bisect.bisect_right(C4, t) - 1; k1 = bisect.bisect_right(C1, t) - 1
    rng = (H[k1 - 24:k1].max() - L[k1 - 24:k1].min()) / A1[k1]
    return s * (c4[k] - S1200[k]) / A4[k], rng, s * (Cc[k1] - S200[k1]) / A1[k1]
q[['sdv', 'rng', 'd200']] = [feats(t, s) for t, s in zip(q.t, q.side)]
q['hour'] = q.t.dt.hour; q['wd'] = q.t.dt.dayofweek; q['h2'] = q.t >= '2020-07-01'; q['hold_h'] = (q.exit_t - q.t).dt.total_seconds() / 3600
def t(r): return r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 2 else np.nan
print(f'Q@US30 n{len(q)} {q.R.mean():+.3f} t{t(q.R):.2f} 前後半 {q[~q.h2].R.mean():+.2f}({(~q.h2).sum()})/{q[q.h2].R.mean():+.2f}({q.h2.sum()}) 買い {q[q.side==1].R.mean():+.2f}({(q.side==1).sum()}) 売り {q[q.side==-1].R.mean():+.2f}({(q.side==-1).sum()})')
print('年:', q.groupby(q.t.dt.year).R.agg(['size', 'sum']).round(1).T.to_string())
for col, bins in (('sdv', [-99, 0, 4, 8, 99]), ('d200', [-99, 0, 2, 4, 99]), ('rng', [0, 3, 4, 5, 99]), ('hour', [-1, 7, 13, 16, 20, 24]), ('band', [-0.5, 0.5, 1.5]), ('imp', [0, 3, 6, 99]), ('op', [-9, 0, 1, 2.5]), ('m20d', [-9, 0, 1, 2, 9]), ('h1sl', [-9, 0.3, 0.7, 9]), ('wd', [-1, 0, 3, 4])):
    g = q.groupby(pd.cut(q[col], bins), observed=True)
    print(f'  {col}: ' + ' | '.join(f'{iv}: n{len(v)} {v.R.mean():+.2f} ({v[~v.h2].R.mean():+.2f}/{v[v.h2].R.mean():+.2f})' for iv, v in g))
r = q.R.sort_values(ascending=False); print('top5:', r.head(5).round(1).tolist(), 'rest mean %+.2f' % r[5:].mean())
