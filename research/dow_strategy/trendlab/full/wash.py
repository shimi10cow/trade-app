import pandas as pd, numpy as np
X = pd.read_pickle('full/current.pkl'); X = X[X.key != 'A@EURUSD']
SP = {'US30': '2020-07-01', 'US500': '2021-10-01', 'JP225': '2021-10-01', 'BTCUSD': '2022-01-01'}
X['half2'] = [t >= pd.Timestamp(SP.get(s, '2016-01-01')) for s, t in zip(X.sym, X.t)]
F = {'日足の向き': lambda x: x.dside == 1, 'H1MA75傾き': lambda x: x.h1sl > 0, 'レベル反発なし': lambda x: x.band == 0,
     'MA20距離>-0.9': lambda x: x.m20d > -0.9, '勢い<=6ATR': lambda x: ~(x.imp > 6), 'H4開き<2.5': lambda x: x.op < 2.5, 'H4傾き<0.35': lambda x: x.sl4 < 0.35}
def t(r): return r.mean() / (r.std(ddof=1) / np.sqrt(len(r))) if len(r) > 2 else np.nan
base = []; cand = []
for k, x in X.groupby('key'):
    r = x.sort_values('t').R; s = np.sort(r)[::-1]; eq = r.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max(); yrs = (x.exit_t.max() - x.t.min()).days / 365.25
    base.append(dict(EA=k, 回数=len(r), 年=round(len(r) / yrs, 1), 平均=round(r.mean(), 2), t=round(t(r), 2), 上位5=f'{s[:5].sum() / r.sum():.0%}', 前半=round(x[~x.half2].R.mean(), 2), 後半=round(x[x.half2].R.mean(), 2), DD_R=round(dd, 1), 年R=round(r.sum() / yrs, 1)))
    for fn, f in F.items():
        keep = f(x); out = x[~keep]
        if len(out) < 8 or keep.all(): continue
        a, b = out[~out.half2].R, out[out.half2].R
        cand.append(dict(EA=k, 条件=fn, 外す回数=len(out), 外す割合=f'{len(out) / len(x):.0%}', 外す分の平均=round(out.R.mean(), 2), 外す分_前半=round(a.mean(), 2) if len(a) else np.nan, 外す分_後半=round(b.mean(), 2) if len(b) else np.nan,
                         残す平均=round(x[keep].R.mean(), 2), 残すt=round(t(x[keep].R), 2), 元t=round(t(x.R), 2), 合計の変化R=round(-out.R.sum(), 1)))
pd.set_option('display.width', 250)
B = pd.DataFrame(base).sort_values('t'); print(B.to_string(index=False)); print()
C = pd.DataFrame(cand)
good = C[(C.外す分_前半 < 0) & (C.外す分_後半 < 0) & (C.残すt > C.元t)].sort_values('外す分の平均')
print('両方の半分で、外す分がマイナス・t が上がる条件:'); print(good.to_string(index=False))
