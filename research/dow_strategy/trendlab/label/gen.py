import json, numpy as np, pandas as pd
x = pd.read_pickle('/home/user/trendlab/x_all.pkl')
x = x[(x.sym != 'XAGUSD') & (x.k == 1) & (pd.to_datetime(x.t) >= '2012-01-01')]
rng = np.random.default_rng(7); samp = []
for sym, g in x.groupby('sym'):
    samp.append(g.sample(6, random_state=int(rng.integers(1e6))))
S = pd.concat(samp).sample(frac=1, random_state=3).reset_index(drop=True)
out = []; key = []; cache = {}
for n, r in S.iterrows():
    if r.sym not in cache: cache[r.sym] = pd.read_pickle(f'/home/user/trendlab/h1_{r.sym}.pkl').reset_index(drop=True)
    h = cache[r.sym]; c = h.c
    m20 = c.rolling(20).mean(); m75 = c.rolling(75).mean()
    i = int(np.flatnonzero(h.t.to_numpy() == np.datetime64(r.t))[0]); i0 = int(np.flatnonzero(h.t.to_numpy() == np.datetime64(r.cross_t))[0])
    a = i - 399; px = float(c.iloc[i]); dg = max(0, 5 - int(np.floor(np.log10(abs(px)))) - 1)
    q = lambda v: [round(float(z), dg) for z in v]
    sl = h.iloc[a:i + 1]
    sid = f's{n + 1:03d}'
    out.append(dict(id=sid, sym=r.sym, s=int(r.s), d=dg, ci=i0 - a, t=str(pd.Timestamp(r.t))[:16],
                    o=q(sl.o), h=q(sl.h), l=q(sl.l), c=q(sl.c), m20=q(m20.iloc[a:i + 1]), m75=q(m75.iloc[a:i + 1]),
                    tt=[str(t)[5:13].replace('T', ' ') for t in sl.t.iloc[::40]]))
    key.append(dict(id=sid, sym=r.sym, t=r.t, s=r.s, R_tp2=r.R_tp2, R_tp3=r.R_tp3, R_trail=r.R_trail, R_ma=r.R_ma))
pd.DataFrame(key).to_pickle('/home/user/trendlab/label/key.pkl')
open('/home/user/trendlab/label/data.js', 'w').write('const DATA=' + json.dumps(out, separators=(',', ':')) + ';')
print(len(out), S.sym.value_counts().to_dict())
