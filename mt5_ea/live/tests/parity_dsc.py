"""2026-11-20: B now skips entries >= 2.0 ATR(H4) from the level (dsc.B_FAR); the research list predates it, so B differs by those trades.
Usage: DSC_RESEARCH=<folder with F_<SYM>_d9.pkl and new_trades_u.pkl> python -m mt5_ea.live.tests.parity_dsc [SYM ...]
2026-11-17: H4 lines now die on a whole-candle break and the line must be alive at the entry; the research copy (scratch deadmode.py body)
and the live code match on all B 133 / C 60 / W 245 trades.
2026-11-15 result: 263 of the 264 research trades reproduced with the same R (live 286 trades, +172.8R vs research +164.7R:
the live code frees a level when its trade closes; research used an older exit time)."""
"""Parity: live mt5_ea/live/eas/dsc.py vs the research trade list (q/new_trades_u.pkl, 7 pairs, 2016-11..2026-10)."""
import sys, pickle, pandas as pd, numpy as np

from mt5_ea.live.eas import dsc
import os; Q=os.environ.get('DSC_RESEARCH', '/tmp/claude-0/-home-user-trade-app/13978ff6-6519-5f05-b953-f01dd0dd89a9/scratchpad/q/')
R=pd.read_pickle(Q+'new_trades_u.pkl'); R=R[R.grp=='7通貨']
syms=sys.argv[1:] or list(dsc.SYMBOLS); out=[]
for sym in syms:
    F=pickle.load(open(Q+f'F_{sym}_d9.pkl','rb'))
    for sc,lab in (('B','B'),('C','C'),('W','ダブル')):
        res=dsc.run(F,sc); T=res['trades']; r=R[(R.sym==sym)&(R.scene==lab)]
        m=set(zip(r.t,r.side)); mt=set(zip(T.t,T.side)) if len(T) else set()
        both=m&mt
        Rl=T.set_index(['t','side']).R if len(T) else pd.Series(dtype=float); Rr=r.set_index(['t','side']).R
        d=[abs(Rl.loc[k]-Rr.loc[k]) for k in both]
        print(f'{sym} {sc}: research {len(r)} {r.R.sum():+.1f}R | live {len(T)} {T.R.sum() if len(T) else 0:+.1f}R open {len(res["open"])} | same entries {len(both)} R diff (median) {np.median(d) if d else 0:.2f}',flush=True)
        out.append(dict(sym=sym,sc=sc,n_r=len(r),R_r=r.R.sum(),n_l=len(T),R_l=T.R.sum() if len(T) else 0,both=len(both)))
pd.DataFrame(out).to_pickle(Q+'parity_dsc.pkl')
