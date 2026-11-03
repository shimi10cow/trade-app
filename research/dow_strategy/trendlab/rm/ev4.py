import pandas as pd, numpy as np, sys
d = pd.concat([pd.read_pickle(f'r4_{s}.pkl') for s in ('EURUSD','USDJPY','XAUUSD')])
def st(x):
    r = x.R.to_numpy(); n = len(r)
    if n < 10: return None
    t = r.mean() / (r.std(ddof=1) / np.sqrt(n)); top = np.sort(r)[::-1][:5].sum()
    a = x[x.t < '2016-01-01'].R; b = x[x.t >= '2016-01-01'].R
    return dict(n=n, avg=round(r.mean(), 3), tot=round(r.sum(), 1), t=round(t, 2), first=round(a.sum(), 1), second=round(b.sum(), 1),
                top5=round(top / r.sum(), 2) if r.sum() > 0 else np.nan, win=round((r > 0).mean(), 2))
out = []
filt = sys.argv[1] if len(sys.argv) > 1 else 'True'
d = d.query(filt) if filt != 'True' else d
for k, x in d.groupby(['tol', 'kind', 'trig', 'stop', 'ex']):
    s = st(x)
    if s: out.append(dict(zip(['tol', 'kind', 'trig', 'stop', 'ex'], k), **s))
o = pd.DataFrame(out).sort_values('t', ascending=False)
print(o.head(int(sys.argv[2]) if len(sys.argv) > 2 else 25).to_string(index=False))
