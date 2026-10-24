"""EA-T variants from the user's review: replace the lagging H4 ER gate with 'which H1 pullback after the SMA20/75 cross'."""
import sys, bisect, pandas as pd, numpy as np
from multiprocessing import Pool
sys.path.insert(0, '/home/user/trade-app/research/dow_strategy')
import regime_ea2 as R2
RE, LV, EC = R2.RE, R2.LV, R2.EC
h1 = R2.h1; C1 = R2.C1
m20 = h1.c.rolling(20).mean().to_numpy(); m75 = R2.MA[75]
rel = np.sign(m20 - m75)
# last cross index (bar where rel changed) for each bar
last_x = np.full(len(rel), -1); lx = -1
for i in range(1, len(rel)):
    if rel[i] != rel[i - 1]: lx = i
    last_x[i] = lx
H1P = R2.H1P; H1PT = R2.H1PT  # (available_time, kind 'hi'/'lo', price)
def pb_count(t, s):
    """returns (cross_ok, n) : n = H1 swing lows (long) confirmed since the cross + 1 = current pullback number"""
    tc = t + pd.Timedelta(minutes=15); k = bisect.bisect_right(C1, tc) - 1
    if k < 0 or rel[k] != s or last_x[k] < 0: return False, 0
    tx = C1[last_x[k]]
    a = bisect.bisect_right(H1PT, tx); b = bisect.bisect_right(H1PT, tc)
    want = 'lo' if s == 1 else 'hi'
    n = sum(1 for j in range(a, b) if H1P[j][1] == want)
    return True, n + 1
def base(t, s): return LV.h1_ok(t, s) and RE.feat(t, s)['side_d'] > 0 and EC.env_ok({'notri': 'H4'}, t + pd.Timedelta(minutes=15), s)
def er(t, s): return RE.feat(t, s)['er'] > 0.10
def pb(maxn):
    def f(t, s):
        ok, n = pb_count(t, s); return ok and n <= maxn
    return f
def both(*fs): return lambda t, s: all(f(t, s) for f in fs)
V = {
  'T_now': both(base, er),
  'noER': base,
  'x2': both(base, pb(2)), 'x3': both(base, pb(3)), 'xall': both(base, pb(99)),
  'ER_x3': both(base, er, pb(3)),
}
def run(k):
    tr = LV.E.run_pair('EURUSD', LV.E.Config(use_long_ma=False, extra_filter=V[k]))
    tr['Rc'] = tr.R - LV.COST / tr.risk
    tr['pbn'] = [pb_count(pd.Timestamp(t), s)[1] for t, s in zip(tr.time, tr.side)]
    tr.to_csv(f'/tmp/tdiag/v_{k}.csv', index=False)
    return k, tr
if __name__ == '__main__':
    with Pool(3) as p:
        for k, tr in p.imap_unordered(run, list(V)):
            y = pd.to_datetime(tr.time).dt.year; tr = tr[y >= 2005]; y = y[y >= 2005]
            f, s = tr[y <= 2015].Rc, tr[y >= 2016].Rc
            pf = lambda r: r[r > 0].sum() / -r[r < 0].sum()
            print(f'{k:6s} n={len(tr):4d} 前半{f.sum():+6.1f}R PF{pf(f):.2f} | 後半{s.sum():+6.1f}R PF{pf(s):.2f}', flush=True)
