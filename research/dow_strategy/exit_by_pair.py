"""Can an EA that fails on a pair be rescued by a different exit? (user, 2026-10-22: 'the entry is fine, it is about
whether the move extends'). Same entries, exits swapped. EAs on the shared runner: J2, J3, EV, C, P (+S on gold/BTC).
Exits: base (each EA's own), m15 trail from +0.5R / +1R (take what the pair gives), hybrid M15->H1, H1 trail from +2R,
H4 swing trail from +1R (let it run). Run inside a pair workspace; writes results/exits/<ea>_<exit>.csv.
Usage: python exit_by_pair.py <SYM>"""
import sys, os
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import turn_tune as TT  # noqa: E402
import j3_ea as J3  # noqa: E402
import step2b_cl15 as CL  # noqa: E402
import pb_ea as PB  # noqa: E402
import st_trend as ST  # noqa: E402
X = TT.X; B = X.B; TE = TT.TE
SYM = sys.argv[1]
OUT = B.HERE / 'results' / 'exits'; OUT.mkdir(parents=True, exist_ok=True)
def jst_hours(ev):
    t = pd.DatetimeIndex([e['t'] - pd.Timedelta(minutes=15) for e in ev]).tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').tz_convert('Asia/Tokyo')
    return np.where(pd.isna(t), -1, t.hour)
def eas():
    E = {}
    E['J2'] = (lambda: TT.h1filter(TT.h1filter(TT.BASEEV, 'h1major'), 'hour0_10'), dict(TT.BASE))
    E['J3'] = (lambda: J3.events(True, False), dict(trig='now', stop='h1prot', buf=0.3, exit='h1', act=1.0, win=1))
    def ev_ev():
        b = TE.events('M15', 'same'); h = jst_hours(b); return [e for e, x in zip(b, h) if 18 <= x < 21 or 0 <= x < 3]
    E['EV'] = (ev_ev, dict(trig='now', stop='ref', buf=0.3, exit='h1', act=1.0, win=1))
    E['C'] = (lambda: CL.EV, dict(CL.BASE, maxdev=4, notri='H4'))
    E['P'] = (lambda: PB.ev_pullback(maxn=3, ma=True, d75=2.5, win=24), dict(trig='dow', stop='h1swing', buf=0.3, exit='h1', act=1.0, env='T2', rs_lo=0.5))
    if SYM in ('XAUUSD', 'BTCUSD'):
        c4, c1, act = ('ma', 'prov', 1.0) if SYM == 'XAUUSD' else ('ma', 'ma', 2.0)
        E['S'] = (lambda: ST.events(c4, c1, 'buy'), dict(trig='dow', stop='m15turn', buf=0.3, exit='h1', act=act, win=1))
    return E
EXITS = {'base': {}, 'm15a05': dict(exit='m15', act=0.5), 'm15a1': dict(exit='m15', act=1.0), 'hyb': dict(exit='hyb', act=1.0, sw=2.0),
         'h1a2': dict(exit='h1', act=2.0), 'h4a1': dict(exit='h4', act=1.0)}
E = eas(); EVS = {k: f() for k, (f, _) in E.items()}
def run1(job):
    ea, ex = job
    cfg = dict(E[ea][1]); cfg.update(EXITS[ex])
    tr = X.run(EVS[ea], cfg); tr.to_csv(OUT / f'{ea}_{ex}.csv', index=False); return ea, ex, len(tr)
if __name__ == '__main__':
    jobs = [(ea, ex) for ea in E for ex in EXITS]
    with Pool(int(os.environ.get('NPROC', '2'))) as p:
        for ea, ex, n in p.imap_unordered(run1, jobs):
            print(ea, ex, n, flush=True)
