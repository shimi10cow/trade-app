"""All live EAs (recommended ON) on broker-time data, today's rules over the whole history. Usage: python port_now.py SYMBOL"""
import pickle, sys
import pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.env import Env
from mt5_ea.live.registry import ADOPTED
from mt5_ea.live.eas import ds as DS, j2 as J2
DS.run_adopted.__defaults__ = (True, False)                # the new DS exit for the whole history
J2.ADOPTED['USDJPY'] = dict(J2.ADOPTED['USDJPY'], cutover=False)   # the H4-stage exit for the whole history
OFF = {'R@EURUSD', 'A@EURUSD', 'RM@EURUSD', 'RM@XAUUSD'}
sym = sys.argv[1]; IDX = sym in ('US30', 'US500', 'JP225', 'US100')
F = pickle.load(open(f'/home/user/trendlab/{"idx" if IDX else "tz"}/frames_{sym}.pkl', 'rb'))
if getattr(F, 'W1', None) is None:
    mb = F.m15_all.set_index('t'); F.W1 = mb.resample('W-MON', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
env = Env(F.m15_all); out = {}
for e in ADOPTED:
    if e.symbol != sym or e.key in OFF:
        continue
    tr = e.run(F, env)['trades'].copy()
    tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]; xc = [c for c in ('exit_t', 'ExitTime') if c in tr][0]
    tr['t'] = pd.to_datetime(tr[tc]); tr['exit_t'] = pd.to_datetime(tr[xc])
    out[e.key] = tr[['t', 'exit_t', 'side', 'R']].copy(); out[e.key]['w'] = e.weight
    print(sym, e.key, len(tr), round(tr.R.sum(), 1), flush=True)
pd.to_pickle(out, f'/home/user/trendlab/check/port_now_{sym}.pkl')
