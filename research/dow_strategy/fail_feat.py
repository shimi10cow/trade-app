"""Loose 'failed push' setups (any H1 higher low after a lower swing): which causal features separate the ones the user
marked (within 12h after / 48h before a point) from the rest, and which features carry forward edge on their own."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fail_ea as F  # noqa: E402
import env_ctx as EC  # noqa: E402
B = F.B; c1 = F.c1; A1 = F.A1; S75 = F.S75; S200 = F.S200
P = pd.read_csv(B.HERE / 'results' / 'user_points_shape.csv', parse_dates=['time'])
ev = pd.DataFrame(F.events(look=30, ma=False, pos='none'))
C1 = B.C1; C4 = B.C4
rows = []
for e in ev.itertuples():
    s = e.side; k = bisect.bisect_right(C1, e.t) - 1; k4 = bisect.bisect_right(C4, e.t) - 1; dd = 'up' if s == 1 else 'down'
    cx = EC.ctx_at(e.t, s)
    hit = ((P.side == s) & ((P.time - e.t) <= pd.Timedelta(hours=12)) & ((e.t - P.time) <= pd.Timedelta(hours=48))).any()
    rows.append(dict(t=e.t, side=s, hit=hit, ma75=s * (c1[k] - S75[k]) / A1[k], ma200=s * (c1[k] - S200[k]) / A1[k],
                     slope75=s * (S75[k] - S75[k - 10]) / A1[k], slope200=s * (S200[k] - S200[k - 30]) / A1[k],
                     l2_vs_75=s * (e.ref - S75[k]) / A1[k], h1=B.R1['bars'][k][0] == dd, h1p=B.R1['prov_bars'][k][0] == dd,
                     h4=B.R4['bars'][k4][0] == dd, h4p=B.R4['prov_bars'][k4][0] == dd, d75=cx['d75'], rs=cx['rs'], sd=cx['sd']))
X = pd.DataFrame(rows)
yrs = set(P.time.dt.year); Xy = X[X.t.dt.year.isin(yrs)]
print(f'ゆるい setup {len(X)}（点のある年 {len(Xy)}、うち点の近く {Xy.hit.sum()}）')
for c in ('h1', 'h1p', 'h4', 'h4p'):
    print(f'  {c}: 点の近く {Xy[Xy.hit][c].mean():.0%} / それ以外 {Xy[~Xy.hit][c].mean():.0%}')
for c in ('ma75', 'ma200', 'slope75', 'slope200', 'l2_vs_75', 'd75', 'rs', 'sd'):
    print(f'  {c:9s}: 点の近く 中央{Xy[Xy.hit][c].median():+.2f} 有利側{(Xy[Xy.hit][c] > 0).mean():.0%} / それ以外 中央{Xy[~Xy.hit][c].median():+.2f} 有利側{(Xy[~Xy.hit][c] > 0).mean():.0%}')
X.to_csv(B.HERE / 'results' / 'fail_loose_feats.csv', index=False)
