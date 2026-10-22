"""All candidates of the night together (2026-10-22): T2, T2 tight-stop x1.5, gold S/Q half each, drawdown throttle."""
import numpy as np, pandas as pd
from pfx import BASE9, BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/all_feat2.pkl'); Q = pd.read_pickle(f'{S}/feat/q_best.pkl'); Qg = Q[Q.pair == 'XAUUSD'].copy()
cut = A[(A.key == 'T2@EURUSD') & (A.half == 1)].stop_atr.quantile(0.2)
def mk(keys, t2w=False, gold=False):
    X = A[A.key.isin(keys)][['R', 'tt', 'et', 'key', 'pair', 'stop_atr']].copy()
    if t2w: X.loc[(X.key == 'T2@EURUSD') & (X.stop_atr < cut), 'R'] *= 1.5
    if gold:
        X.loc[X.key == 'S@XAUUSD', 'R'] *= 0.5; g = Qg.copy(); g['R'] *= 0.5; X = pd.concat([X, g])
    return X.sort_values('et')
def sim(X, lo, hi, risk, D=1.0, m=1.0):
    d = X[(X.et.dt.year >= lo) & (X.et.dt.year <= hi)]
    eq = pk = 1.0; mdd = 0; yr = {}; pk_t = d.et.iat[0]; uw = pd.Timedelta(0)
    for r, t in zip(d.R.to_numpy(), d.et):
        k = m if eq < pk * (1 - D) else 1.0; y0 = eq; eq *= 1 + risk * k * r; yr[t.year] = yr.get(t.year, 1) * eq / y0
        if eq >= pk: pk = eq; pk_t = t
        else: uw = max(uw, t - pk_t)
        mdd = min(mdd, eq / pk - 1)
    return eq ** (1 / (hi - lo + 1)) - 1, mdd, min(yr.values()) - 1, uw.days / 30.4
def boot(X, risk, D=1.0, m=1.0, n=1500):
    ms = pd.period_range('2005-01', '2026-09', freq='M'); byM = {k: g.R.to_numpy() for k, g in X.groupby(X.et.dt.to_period('M'))}
    seqs = [byM.get(k, np.array([])) for k in ms]; rng = np.random.default_rng(5); dd = []; fin = []
    for _ in range(n):
        r = np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 120)]); eq = pk = 1.0; md = 0
        for x in r:
            k = m if eq < pk * (1 - D) else 1.0; eq *= 1 + risk * k * x; pk = max(pk, eq); md = min(md, eq / pk - 1)
        dd.append(md); fin.append(eq)
    dd = np.array(dd); return np.median(fin) ** 0.1 - 1, np.median(dd), np.percentile(dd, 10), (dd < -0.3).mean()
SETS = [('① 現行 9 本', mk(BASE9), 1, 1), ('② T→T2', mk(BASE9T2), 1, 1), ('③ ＋T2 狭い損切り×1.5', mk(BASE9T2, True), 1, 1),
        ('④ ＋ゴールド S/Q 半分ずつ', mk(BASE9T2, True, True), 1, 1), ('⑤ ＋DD10%超で半分', mk(BASE9T2, True, True), 0.10, 0.5)]
print('### 前半で DD -20% にそろえた場合')
print('| 組み合わせ | 1回のリスク | 前半 年利 | 前半 最悪年 | 後半 年利 | 後半 DD | 後半 最悪年 | 後半 最長の負け期間 |')
for lab, X, D, m in SETS:
    a, b = 0.001, 0.05
    for _ in range(25):
        mid = (a + b) / 2
        if sim(X, 2005, 2015, mid, D, m)[1] < -0.20: b = mid
        else: a = mid
    f = sim(X, 2005, 2015, a, D, m); s = sim(X, 2016, 2026, a, D, m)
    print(f'| {lab} | {a:.2%} | {f[0]:.1%} | {f[2]:.1%} | {s[0]:.1%} | {s[1]:.1%} | {s[2]:.1%} | {s[3]:.0f}か月 |', flush=True)
print('\n### 月の並べ替え 10 年（2005-2026 の月から）')
print('| 組み合わせ | 1回のリスク | 年利(中央) | DD中央 | DD悪い方10% | -30%超の確率 |')
for lab, X, D, m in SETS:
    for risk in (0.0075, 0.01):
        g, d50, d10, p = boot(X, risk, D, m)
        print(f'| {lab} | {risk:.2%} | {g:.1%} | {d50:.0%} | {d10:.0%} | {p:.0%} |', flush=True)
