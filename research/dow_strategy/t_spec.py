"""EA-T specialised with the user's pullback counter (2026-10-21). Base = EA-T (stochastic pullback, no long MA, H1 Dow,
daily side, no H4 triangle). Variants replace / add to the lagging H4 ER200 gate:
  pull number (pb_ea counter, K=2 ATR) <= maxn, H1 distance from SMA75 >= d75 ATR, H1 SMA20/75 same side.
Usage: EA_M15_CACHE=... python dow_strategy/t_spec.py [keys]"""
import sys, bisect, os
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import regime_ea2 as R2  # noqa: E402
import pb_ea as PB  # noqa: E402
RE, LV, EC = R2.RE, R2.LV, R2.EC
ST = PB.counter(2.0); CLH = list(PB.CL)


def h1i(t):
    return bisect.bisect_right(CLH, t + pd.Timedelta(minutes=15)) - 1


def base(t, s):
    return LV.h1_ok(t, s) and RE.feat(t, s)['side_d'] > 0 and EC.env_ok({'notri': 'H4'}, t + pd.Timedelta(minutes=15), s)


def er(t, s):
    return RE.feat(t, s)['er'] > 0.10


def gate(maxn=None, d75=None, ma=False):
    def f(t, s):
        i = h1i(t)
        if i < 0:
            return False
        side, n, armed, _ = ST[i]
        if maxn is not None and (side != s or n + armed > maxn):
            return False
        if d75 is not None and not (s * (PB.cc[i] - PB.M75[i]) >= d75 * PB.A1[i]):
            return False
        if ma and np.sign(PB.M20[i] - PB.M75[i]) != s:
            return False
        return True
    return f


def both(*fs):
    return lambda t, s: all(f(t, s) for f in fs)


V = {
    'T_now': both(base, er),
    'T_noER': base,
    'T_n3': both(base, gate(3)),
    'T_n2': both(base, gate(2)),
    'T_n3_d17': both(base, gate(3, 1.7)),
    'T_d17': both(base, gate(None, 1.7)),
    'T_n3_ma': both(base, gate(3, None, True)),
    'T_ER_n3': both(base, er, gate(3)),
}


def run(k):
    tr = LV.E.run_pair('EURUSD', LV.E.Config(use_long_ma=False, extra_filter=V[k]))
    tr['Rc'] = tr.R - LV.COST / tr.risk
    tr.to_csv(PB.OUT / f'tspec_{k}.csv', index=False)
    return k, tr


if __name__ == '__main__':
    keys = sys.argv[1:] or list(V)
    pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r < 0].sum())
    with Pool(int(os.environ.get('NPROC', '3'))) as p:
        for k, tr in p.imap_unordered(run, keys):
            t = pd.to_datetime(tr.time); tr = tr[t.dt.year >= 2005]; y = t[t.dt.year >= 2005].dt.year
            f, s = tr[y <= 2015].Rc, tr[y >= 2016].Rc
            eq = tr.sort_values('time').Rc.cumsum(); dd = (eq - eq.cummax()).min()
            tt = tr.assign(t=pd.to_datetime(tr.time), side=tr.side)
            print(f'{k:10s} 前半 {len(f):4d}回 {f.sum():+6.1f}R PF{pf(f):.2f} | 後半 {len(s):4d}回 {s.sum():+6.1f}R PF{pf(s):.2f} | DD{dd:6.1f} {PB.coverage(tt)}', flush=True)
