import pandas as pd, numpy as np
exec(open('full/eval.py').read().split("# ---------- 1 filters")[0])
X = pd.read_pickle('full/current.pkl')[['key', 'sym', 't', 'exit_t', 'R', 'side', 'w', 'mult']]; X = X[X.key != 'A@EURUSD']
d = pd.concat([pd.read_pickle(f'rm/r8_{s}.pkl') for s in ('EURUSD', 'XAUUSD')])
d = d[(d.kind == 'PRV') & (d.pre_bars >= 50) & (d.trig == 'D') & (d.stop == 'LO') & (d.ex == 'M2') & (d.brk <= 0.5)]
y = pd.DataFrame(dict(key='RM@' + d.sym.values, sym=d.sym.values, t=pd.to_datetime(d.t.values), exit_t=pd.to_datetime(d.exit_t.values), R=d.R.values, side=d.side.astype(int).values, w=1.0))
y['mult'] = [calendar_mult(s, sd, t, tdm(s, t)) for s, sd, t in zip(y.sym, y.side, y.t)]
def path(X, risk, half=True):
    X = X.sort_values('exit_t'); eq = pk = 1.0; mdd = 0.0; yr = {}; e0 = {}
    for r, k, w, t in zip(X.R, X.mult, X.w, X.exit_t):
        e0.setdefault(t.year, eq)
        eq *= 1 + risk * k * w * (0.5 if (half and eq < 0.9 * pk) else 1.0) * r; pk = max(pk, eq); mdd = min(mdd, eq / pk - 1); yr[t.year] = eq
    yrs = (X.exit_t.max() - X.t.min()).days / 365.25
    ys = pd.Series({k: yr[k] / e0[k] - 1 for k in yr}); ys = ys.iloc[1:-1]
    return eq ** (1 / yrs) - 1, mdd, ys
mo = X.assign(Rw=X.R * X.w).groupby(X.exit_t.dt.to_period('M')).Rw.sum(); bad = set(mo[mo <= mo.quantile(0.2)].index)
m = y.groupby(y.exit_t.dt.to_period('M')).R.sum(); j = pd.concat([m, mo], axis=1).fillna(0); j = j[j.index >= y.t.min().to_period('M')]
print(f'RM（ユーロドル・ゴールド）: {len(y)}回 年{len(y)/22:.1f}回 合計{y.R.sum():+.1f}R 月の相関 {j.iloc[:,0].corr(j.iloc[:,1]):+.2f} 全体の悪い月(下位20%)での合計 {y[y.exit_t.dt.to_period("M").isin(bad)].R.sum():+.1f}R')
ov = sum(((X.sym == s) & (X.t < e) & (X.exit_t > t)).any() for s, t, e in zip(y.sym, y.t, y.exit_t)); print(f'同じ銘柄の他EAと保有が重なる: {ov}/{len(y)}回')
A = pd.concat([X, y]); out = []
for risk in (0.01, 0.015, 0.02):
    for lab, Z in (('今の20本', X), ('＋RM', A)):
        g, dd, ys = path(Z, risk)
        out.append(dict(リスク=f'{risk:.1%}', 構成=lab, 年利=f'{g:+.1%}', 最大DD=f'{dd:.1%}', 最悪の年=f'{ys.min():+.1%}', マイナス年=f'{(ys < 0).sum()}/{len(ys)}', 回数=len(Z)))
print(pd.DataFrame(out).to_string(index=False))
g0, _, y0 = path(X, 0.01); g1, _, y1 = path(A, 0.01)
yy = pd.DataFrame({'今': y0, '+RM': y1}); yy['差'] = yy['+RM'] - yy['今']; yy['RMのR'] = y.groupby(y.exit_t.dt.year).R.sum()
print((yy * [100, 100, 100, 1]).round(1).fillna(0).to_string())
