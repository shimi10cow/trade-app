import pandas as pd, numpy as np
exec(open('full/eval.py').read().split("# ---------- 1 filters")[0])
X = pd.read_pickle('full/current.pkl')[['key', 'sym', 't', 'exit_t', 'R', 'side', 'w', 'mult']]
X = X[X.key != 'A@EURUSD']
d = pd.concat([pd.read_pickle(f'rm/r4_{s}.pkl') for s in ('EURUSD', 'USDJPY', 'XAUUSD')])
d = d[(d.tol == 0.2) & (d.trig == 'D') & (d.stop == 'LO') & (d.ex == 'M2') & (d.pre_bars >= 50)]
def mk(x, key):
    y = pd.DataFrame(dict(key=key + '@' + x.sym.values, sym=x.sym.values, t=pd.to_datetime(x.t.values), exit_t=pd.to_datetime(x.exit_t.values), R=x.R.values, side=x.side.astype(int).values, w=1.0))
    y['mult'] = [calendar_mult(s, sd, t, tdm(s, t)) for s, sd, t in zip(y.sym, y.side, y.t)]; return y
C = {'RM 仮転換だけ': mk(d[d.kind == 'PRV'], 'RM'),
     'RM 仮＋本': mk(d.sort_values('kind', ascending=False).drop_duplicates(['sym', 't', 'side']), 'RM')}
def port(X, risk=0.01, half=True):
    X = X.sort_values('exit_t'); eq = pk = 1.0; mdd = 0.0
    for r, k, w in zip(X.R, X.mult, X.w):
        eq *= 1 + risk * k * w * (0.5 if (half and eq < 0.9 * pk) else 1.0) * r; pk = max(pk, eq); mdd = min(mdd, eq / pk - 1)
    yrs = (X.exit_t.max() - X.t.min()).days / 365.25; return eq ** (1 / yrs) - 1, mdd
mo = X.assign(Rw=X.R * X.w).groupby(X.exit_t.dt.to_period('M')).Rw.sum(); bad = set(mo[mo <= mo.quantile(0.2)].index)
a = port(X); b = port(X, 0.02); print(f'今の20本（A・R抜き）: 1% {a[0]:+.1%}/{a[1]:.1%}  2% {b[0]:+.0%}/{b[1]:.1%}  回数 {len(X)}')
for k, y in C.items():
    a = port(pd.concat([X, y])); b = port(pd.concat([X, y]), 0.02)
    m = y.groupby(y.exit_t.dt.to_period('M')).R.sum(); j = pd.concat([m, mo], axis=1).fillna(0); j = j[j.index >= y.t.min().to_period('M')]
    inbad = y[y.exit_t.dt.to_period('M').isin(bad)].R.sum(); yrs = (y.exit_t.max() - y.t.min()).days / 365.25
    ov = sum(((X.sym == s) & (X.t < e) & (X.exit_t > t)).any() for s, t, e in zip(y.sym, y.t, y.exit_t))
    print(f'{k}: {len(y)}回 年{len(y)/yrs:.1f}回 年{y.R.sum()/yrs:+.1f}R 月の相関 {j.iloc[:,0].corr(j.iloc[:,1]):+.2f} 全体の悪い月での合計 {inbad:+.1f}R 同じ銘柄の他EAと保有が重なる {ov}回 | 足すと 1% {a[0]:+.1%}/{a[1]:.1%}  2% {b[0]:+.0%}/{b[1]:.1%}')
    print('   銘柄別', y.groupby('sym').R.agg(['size', 'sum']).round(1).to_dict('index'))
