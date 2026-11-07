"""C / DS / J2 with the rules before 2026-11-06/07 (no C H1-SMA75 filter, DS h1s15 without the H4 step, J2 without the H4-stage exit)."""
import pickle, sys
import pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.env import Env
from mt5_ea.live.registry import BY_KEY
from mt5_ea.live.eas import ds as DS, j2 as J2, c as C_
sym = sys.argv[1]; IDX = sym in ('US30', 'US500', 'JP225', 'US100')
F = pickle.load(open(f'/home/user/trendlab/{"idx" if IDX else "tz"}/frames_{sym}.pkl', 'rb')); env = Env(F.m15_all)
C_.run.__defaults__ = C_.run.__defaults__[:-1] + (None,)          # h1dev off
DS.run_adopted.__defaults__ = (True, False)
for k in ('JP225', 'US500'):
    DS.ADOPTED[k] = {kk: vv for kk, vv in DS.ADOPTED[k].items() if kk != 'exits'} | dict(exit='h1s15')
J2.ADOPTED['USDJPY'] = dict(J2.ADOPTED['USDJPY'], late_legs=None)
out = {}
for key in {'EURUSD': ['C@EURUSD'], 'USDJPY': ['C@USDJPY', 'J2@USDJPY'], 'JP225': ['DS@JP225'], 'US500': ['DS@US500']}[sym]:
    tr = BY_KEY[key].run(F, env)['trades'].copy()
    tr['t'] = pd.to_datetime(tr.t); tr['exit_t'] = pd.to_datetime(tr.exit_t); tr['w'] = 1.0
    out[key] = tr[['t', 'exit_t', 'side', 'R', 'w']]; print(sym, key, len(tr), round(tr.R.sum(), 1), flush=True)
pd.to_pickle(out, f'/home/user/trendlab/check/port_old_{sym}.pkl')
