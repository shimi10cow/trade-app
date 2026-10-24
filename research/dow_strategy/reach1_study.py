"""Trades that reached +1R: what separates the ones that still lost (-1R) from the ones that won?
Chart-based features (all causal at entry or at the bar where +1R was first touched):
  room_h1/room_h4 : distance from entry to the nearest opposite H1/H4 swing (prior high for a buy) in R, known at entry
  hit_h1/hit_h4   : +1R was touched at/after crossing that swing? (price reached the old high)
  t1              : M15 bars from entry to +1R (speed)
  h1/h4 with      : H1/H4 major trend in the trade direction at entry
  d75             : distance from H4 SMA75 at entry (ATR), rs = range score
  brk15           : at +1R, had price broken the last M15 swing high that existed at entry (made a new high)?"""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape as S1  # noqa: E402
import env_ctx as EC  # noqa: E402
B = S1.B; T = S1.T; H, L, C, N = S1.H, S1.L, S1.C, S1.N
C1 = list(B.C1); C4 = list(B.C4)
def piv(R, CL):
    P = sorted(((CL[e['available_idx']], e['kind'], e['price']) for e in R['pivot_events']), key=lambda x: x[0]); return P, [x[0] for x in P]
P1, P1T = piv(B.R1, C1); P4, P4T = piv(B.R4, C4)
P15 = S1.PA, S1.PK, S1.PP
def room(P, PT, t, s, entry, risk, n=12):
    j = bisect.bisect_right(PT, t) - 1; k = 'hi' if s == 1 else 'lo'; c = 0
    while j >= 0 and c < 200:
        if P[j][1] == k and s * (P[j][2] - entry) > 0:
            return s * (P[j][2] - entry) / risk
        j -= 1; c += 1
    return np.nan
TR, yrs = S1.load_all(); rows = []
for nm, t in TR.items():
    for x in t.itertuples():
        s = x.side; ie = min(x.ie, N - 1)
        if x.i0 >= ie:
            continue
        fav = (H[x.i0:ie] - x.entry) / x.risk if s == 1 else (x.entry - L[x.i0:ie]) / x.risk
        k = np.nonzero(fav >= 1)[0]
        if not len(k):
            continue
        i1 = x.i0 + k[0]; te = T[x.i0]; dd = 'up' if s == 1 else 'down'
        k1 = bisect.bisect_right(C1, te) - 1; k4 = bisect.bisect_right(C4, te) - 1
        r1 = room(P1, P1T, te, s, x.entry, x.risk); r4 = room(P4, P4T, te, s, x.entry, x.risk)
        # last M15 swing (opposite kind) known at entry
        j = np.searchsorted(S1.PA, x.i0) - 1
        while j >= 0 and S1.PK[j] != ('hi' if s == 1 else 'lo'):
            j -= 1
        sw = S1.PP[j] if j >= 0 else np.nan
        brk = s * ((H[x.i0:i1 + 1].max() if s == 1 else L[x.i0:i1 + 1].min()) - sw) > 0
        cx = EC.ctx_at(te, s)
        rows.append(dict(ea=nm, lose=x.R <= 0, R=x.R, room_h1=r1, room_h4=r4, t1=i1 - x.i0, brk15=brk,
                         h1=B.R1['bars'][k1][0] == dd, h4=B.R4['bars'][k4][0] == dd, h4p=B.R4['prov_bars'][k4][0] == dd, d75=cx['d75'], rs=cx['rs'], sd=cx['sd'],
                         mfe=fav.max()))
d = pd.DataFrame(rows)
print(f'+1R到達 {len(d)}回 → 負け {d.lose.sum()}回 ({d.lose.mean():.0%}) 合計{d.R.sum():+.0f}R')
def tab(col, q=None):
    g = pd.qcut(d[col], q, duplicates='drop') if q else d[col]
    print(d.groupby(g, observed=True).agg(n=('R', 'size'), 負け率=('lose', 'mean'), 平均R=('R', 'mean')).round(2).to_string(), '\n')
for c in ('ea', 'h1', 'h4', 'h4p', 'brk15'):
    tab(c)
for c in ('room_h1', 'room_h4', 't1', 'd75', 'rs', 'sd'):
    tab(c, 4)
d.to_csv(B.HERE / 'results' / 'reach1_features.csv', index=False)
