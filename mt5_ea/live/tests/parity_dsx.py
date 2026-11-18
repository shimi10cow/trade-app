"""Parity: DX@ (mt5_ea/live/eas/dsc.py scene 'X') vs the research run (scratchpad q20: dx3 -> dx3f -> dx3s -> dx3tp -> d1ma2 -> dbot2 -> dx_line.pkl).
Usage: DSC_RESEARCH=<folder with F_<SYM>_d9.pkl and dx_line.pkl> python -m mt5_ea.live.tests.parity_dsx [SYM ...]
Research costs per symbol as parity_dsr. Indices buy only (sides=(1,)).
2026-11-18 result (13 symbols): live 108 trades +1.012R, research 109 +0.996R; 108 the same entries with the same R. The one research-only
trade (EURJPY 2023-09-13) had the gateway stop 0.08 ATR away; the live code skips stops of 0.05 ATR or less from the entry, the research
simulation had no such check, so the live rule is the intended one."""
import os, sys, pickle, pandas as pd

from mt5_ea.live.eas import dsc
Q = os.environ.get('DSC_RESEARCH', '/tmp/claude-0/-home-user-trade-app/13978ff6-6519-5f05-b953-f01dd0dd89a9/scratchpad/q20/')
QS = os.path.join(os.path.dirname(Q.rstrip('/')), 'q') + '/'
COSTX = dict(GOLD=0.35, SILVER=0.03, US30=3.0, US500=0.6, US100=2.0, JP225=10.0, BTCUSD=40.0)
SUB_Q = ('AUDJPY', 'AUDUSD', 'SILVER', 'US30', 'US500', 'US100', 'JP225'); IDX = ('US30', 'US500', 'US100', 'JP225')
START = {'BTCUSD': '2014-01-01', **{s: '2016-11-01' for s in SUB_Q}}
SYMS = ('EURUSD', 'EURJPY', 'GBPJPY', 'GBPUSD', 'GOLD', 'BTCUSD') + SUB_Q
R = pd.read_pickle(Q + 'dx_line.pkl')
for sym in sys.argv[1:] or SYMS:
    F = pickle.load(open((QS if sym in SUB_Q else Q) + f'F_{sym}_d9.pkl', 'rb'))
    if sym in COSTX:
        F.COST = COSTX[sym]
    T = dsc.run(F, 'X', start=pd.Timestamp(START.get(sym, '2006-11-01')), sides=(1,) if sym in IDX else None)['trades']; r = R[R.sym == sym]
    both = set(zip(pd.to_datetime(T.t), T.side)) & set(zip(pd.to_datetime(r.t), r.side)) if len(T) else set()
    print(f'{sym}: research {len(r)} {r.R.mean() if len(r) else 0:+.3f}R | live {len(T)} {T.R.mean() if len(T) else 0:+.3f}R/trade | same entries {len(both)}')
