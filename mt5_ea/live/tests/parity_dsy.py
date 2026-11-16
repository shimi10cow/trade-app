"""Parity: DY@ (mt5_ea/live/eas/dsc.py scene 'Y') vs the research run (wide2.py d1 mode, touch >= 4, exit H4 then H1 from +3R).
Usage: DSC_RESEARCH=<folder with F_<SYM>_d9.pkl and w_d1_h43.pkl> python -m mt5_ea.live.tests.parity_dsy [SYM ...]
2026-11-16 result (7 pairs, 5 x 20 years + AUD 10 years): live 429 trades +0.560R, research 425 +0.562R, 421 the same entries
with the same R (the rest: a different first setup on the same level, and one trade still open at the end)."""
import os, sys, pickle, pandas as pd

from mt5_ea.live.eas import dsc
Q = os.environ.get('DSC_RESEARCH', '/tmp/claude-0/-home-user-trade-app/13978ff6-6519-5f05-b953-f01dd0dd89a9/scratchpad/q20/')
R = pd.read_pickle(Q + 'w_d1_h43.pkl'); R = R[R.touch >= dsc.Y_TOUCH_MIN]
for sym in sys.argv[1:] or list(dsc.SYMBOLS):
    F = pickle.load(open(Q + f'F_{sym}_d9.pkl', 'rb')); T = dsc.run(F, 'Y')['trades']; r = R[R.sym == sym]
    both = set(zip(pd.to_datetime(T.t), T.side)) & set(zip(pd.to_datetime(r.t), r.side)) if len(T) else set()
    print(f'{sym}: research candidates {len(r)} | live {len(T)} {T.R.mean() if len(T) else 0:+.3f}R/trade | same entries {len(both)}')
