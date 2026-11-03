import pandas as pd, numpy as np, glob
d = pd.concat([pd.read_pickle(f) for f in glob.glob('/home/user/trendlab/exit/e_*.pkl')])
X = pd.read_pickle('/home/user/trendlab/full/current.pkl'); X = X[(X.key != 'A@EURUSD')]
M = X[X.key.str.startswith('M@')][['key', 'sym', 't', 'exit_t', 'R', 'w', 'mult']]
def build(ch):
    parts = [M]
    for k, x in d.groupby('key'):
        v = ch.get(k)
        y = x[['key', 'sym', 't', 'w', 'mult']].copy()
        y['R'] = x[v] if v else x.R; y['exit_t'] = x['x_' + v] if v else x.exit_t; parts.append(y)
    return pd.concat(parts)
def port(Z, risk, half=True):
    Z = Z.sort_values('exit_t'); eq = pk = 1.0; mdd = 0.0; yr = {}; e0 = {}
    for r, k, w, t in zip(Z.R, Z.mult, Z.w, Z.exit_t):
        e0.setdefault(t.year, eq); eq *= 1 + risk * k * w * (0.5 if (half and eq < 0.9 * pk) else 1.0) * r; pk = max(pk, eq); mdd = min(mdd, eq / pk - 1); yr[t.year] = eq
    yrs = (Z.exit_t.max() - Z.t.min()).days / 365.25; ys = pd.Series({k: yr[k] / e0[k] - 1 for k in yr}).iloc[1:-1]
    R = Z.R * Z.w; eqR = R.cumsum(); ddR = (eqR.cummax().clip(lower=0) - eqR).max()
    return f'年利 {eq ** (1 / yrs) - 1:+.1%} 最大DD {mdd:.1%} 最悪の年 {ys.min():+.1%} | 合計 {R.sum():+.0f}R DD {ddR:.1f}R PF {R[R > 0].sum() / -R[R < 0].sum():.2f} 勝率 {(Z.R > 0).mean():.0%}'
A = {'L@EURUSD': 'H1_2', 'DS@XAUUSD': 'H4_1', 'P@USDJPY': 'HYB', 'T2@EURUSD': 'M15_3', 'DS@US500': 'M15_3', 'P@XAUUSD': 'H1_2'}
B = dict(A, **{'Q@XAUUSD': 'H4_2', 'S@XAUUSD': 'H4_2', 'P@XAUUSD': 'H4_2', 'T2@EURUSD': 'H4_1'})
for lab, ch in (('今', {}), ('A: t が上がる 6 本だけ変える', A), ('B: A ＋ ゴールドの Q・S・P と T2 を H4 で追う', B)) + tuple((f'1 本だけ: {k} → {v}', {k: v}) for k, v in A.items()):
    Z = build(ch); print(f'{lab}'); print(f'   1%: {port(Z, 0.01)}'); print(f'   2%: {port(Z, 0.02)}')
