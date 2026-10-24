import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import fail_ea as F  # noqa: E402
P = pd.read_csv(F.B.HERE / 'results' / 'user_points_shape.csv', parse_dates=['time'])
for k, kw in (('base', {}), ('noma', dict(ma=False)), ('look60', dict(look=60)), ('全部ゆるく', dict(look=30, ma=False, pos='none'))):
    ev = pd.DataFrame(F.events(**{**dict(look=120, ma=True, pos='75', hlmin=0.0, win=24), **kw}))
    hit = []
    for p in P.itertuples():
        e = ev[(ev.side == p.side) & ((ev.t - p.time) <= pd.Timedelta(hours=12)) & ((p.time - ev.t) <= pd.Timedelta(hours=48))]
        hit.append(len(e) > 0)
    P['hit'] = hit
    print(f"{k:8s} setup{len(ev):5d}  点を拾えた: 全体{P.hit.mean():.0%} / 下げ失敗型{P[P.typ == 'fail'].hit.mean():.0%} / 押し目型{P[P.typ == 'pull'].hit.mean():.0%}")
