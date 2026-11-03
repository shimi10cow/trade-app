"""Expand the live EAs to other markets (2026-11-03, user): every live EA with its CURRENT rules and settings, run as is on
another symbol's full-history live Frames. No new conditions. R is re-costed with the symbol's own cost (research price space).
Usage: python run.py GBPUSD   -> expand/x_GBPUSD.pkl (rows: ea, t, exit_t, side, R)
"""
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.env import Env
from mt5_ea.live.eas import c as C_, ds as DS, j2 as J2, l as L_, nt as NT, q as Q, rm as RM, rt as RT, s as S_
from mt5_ea.live.eas.pgate import gate as pgate
from mt5_ea.live.eas.h4gate import gate
from mt5_ea.live.eas.wave import axis_filter

sym = sys.argv[1]
COST = {'GBPUSD': 1.5e-4, 'AUDUSD': 1.3e-4, 'USDCAD': 2e-4, 'USDCHF': 2e-4, 'EURJPY': 2e-4, 'AUDJPY': 2.5e-4, 'CADJPY': 3e-4, 'CHFJPY': 3e-4,
        'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4}.get(sym, 2e-4)
IDX = {'US30': 1.5e-4, 'US500': 2e-4, 'US100': 2e-4, 'GER40': 1.5e-4, 'UK100': 1.5e-4, 'EU50': 3e-4, 'OIL': 6e-4, 'BRENT': 6e-4, 'NGAS': 6e-3, 'JP225': 3e-4}
if sym in IDX:
    COST = IDX[sym]; F = pickle.load(open(f'/home/user/trendlab/idx/frames_{sym}.pkl', 'rb'))
else:
    F = pickle.load(open(f'/home/user/trendlab/live_frames_{sym}.pkl', 'rb'))
env = Env(F.m15_all)
NT.COST.setdefault(sym, COST)

EAS = {
    'T2': lambda: axis_filter(F, RT.run(F, 'T1t', env=env)),
    'T': lambda: pgate(gate(lambda F_, e_: RT.run(F, 'T1u', env=env), 'open'), 'band')(F, env),
    'L': lambda: L_.run(F, env=env),
    'L2': lambda: L_.run(F, room=1.0, env=env),
    'C': lambda: pgate(lambda F_, e_: C_.run(F, env=env), 'ext')(F, env),
    'C_jpy': lambda: gate(lambda F_, e_: C_.run(F, strength=True, notri=False, env=env), 'open')(F, env),
    'J2': lambda: J2.run(F, **J2.ADOPTED['USDJPY']),
    'S_xau': lambda: S_.run(F, *S_.ADOPTED['XAUUSD']),
    'Q_xau': lambda: Q.run(F, *Q.ADOPTED['XAUUSD']),
    'Q_xag': lambda: gate(lambda F_, e_: Q.run(F, *Q.ADOPTED['XAGUSD']), 'open')(F, env),
    'Q_us30': lambda: gate(lambda F_, e_: Q.run(F, *Q.ADOPTED['US30']), 'open')(F, env),
    'DS_left': lambda: DS.run_variant(F, 'H1', 'left', 'h1'),
    'DS_sh': lambda: DS.run_variant(F, 'H1', 'shoulder', 'h1'),
    'P': lambda: NT.run(F, sym, seed=False),
    'RM': lambda: RM.run(F),
}
rows = []
for name, fn in EAS.items():
    try:
        r = fn()
    except Exception as ex:
        print(sym, name, 'ERROR', repr(ex)[:200], flush=True); continue
    tr = r['trades']
    if not isinstance(tr, pd.DataFrame) or not len(tr):
        print(sym, name, 0, flush=True); continue
    tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]
    x = pd.DataFrame(dict(ea=name, sym=sym, t=pd.to_datetime(tr[tc]), exit_t=pd.to_datetime(tr['exit_t']), side=tr.side.astype(int), R=tr.R.astype(float),
                          risk=tr['risk'].astype(float) if 'risk' in tr else np.nan))
    x = x[x.t >= ('2017-07-01' if sym in IDX else '2005-06-01')]
    base = NT.COST.get(sym, 1.2e-4) if name == 'P' else 1.2e-4          # cost the code already took
    x['R'] = np.where(np.isfinite(x.risk), x.R + base / x.risk - COST / x.risk, x.R)
    rows.append(x); print(sym, name, len(x), f'{x.R.mean():+.3f}', flush=True)
pd.concat(rows).to_pickle(f'/home/user/trendlab/expand/x_{sym}.pkl'); print('done', sym, flush=True)
