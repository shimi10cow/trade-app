"""Same as port_new3 but judged only on 2022-2026 (the new instruments' own second half): same-risk bootstrap of
2022-26 months, and the real 2022-26 path at a fixed 0.5 % risk."""
import numpy as np, pandas as pd, pfx, combo_stable as CS, new_summary as N
S = N.S; pf = N.pf
C = pd.read_pickle(f'{S}/feat/new3_cands.pkl')
keys4 = CS.P['④ ③＋US30（T・Q）']; base = CS.mk(keys4); base['tt'] = pd.to_datetime(base.tt); base['et'] = pd.to_datetime(base.et)
cols = ['R', 'tt', 'et', 'key', 'pair']
def show(lab, X):
    r, g, d = pfx.boot(X, 2022, 2026)
    Y = X[X.et.dt.year >= 2022].sort_values('et'); eq = np.cumprod(1 + 0.005 * Y.R.to_numpy()); dd = (eq / np.maximum.accumulate(eq) - 1).min()
    print(f'{lab:28s} 2022-26 同じ危険度 年{g:5.1%}(リスク{r:.2%}) DD中央{d:6.1%} | 0.5%固定 年{eq[-1] ** (1 / 4.8) - 1:5.1%} DD{dd:6.1%}', flush=True)
show('④ 基準', base[cols])
for k in sorted(C.key.unique()):
    g = C[C.key == k]; a = g[g.half == 1].R; b = g[g.half == 2].R
    print(f'   {k}: 前半 {a.sum():+.0f}R PF{pf(a):.2f} → 後半 {b.sum():+.0f}R PF{pf(b):.2f}')
    show(f'④＋{k}', pd.concat([base[cols], g[cols]]))
