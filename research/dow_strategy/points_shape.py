"""Classify the user's wanted points by shape (H1 swings known at the point, buy side shown; sell mirrored):
  fail  = 'tried to fall and failed': before the point the market was falling (H1 SMA75 fell over the prior 3 days or the
          H1/H4 major trend was down within the last 5 days), then the latest H1 swing low is HIGHER than the previous one
          (no new low = the fall failed) and price is back above the H1 swing high between them (neckline / inverse H&S).
  pull  = pullback in an existing trend: H1 SMA75 already rising for 3 days and H1 major trend up.
Also: SMA75 slope now (turning up?), how many failed attempts (equal/higher lows), depth of the last low vs the previous."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import user_marks_study as U  # noqa: E402
B = U.B
D = pd.read_csv(B.HERE / 'results' / 'user_points.csv', parse_dates=['time'])
C1 = B.C1; h1 = B.h1; c1 = h1.c.to_numpy(float); A1 = U.A1; s75 = pd.Series(c1).rolling(75).mean().to_numpy()
P1 = sorted(((C1[e['available_idx']], e['idx'], e['kind'], e['price']) for e in B.R1['pivot_events'] if e.get('action', 'confirm') == 'confirm'), key=lambda x: x[0])
P1T = [p[0] for p in P1]
C4 = B.C4
def hist(arr, k):
    return arr[k] if k >= 0 else None
rows = []
for p in D.itertuples():
    s = p.side; t = p.time + pd.Timedelta(hours=1 if p.tf == 'H1' else 4 if p.tf == 'H4' else 0.25)
    k1 = bisect.bisect_right(C1, t) - 1; a = A1[k1]
    j = bisect.bisect_right(P1T, t)
    pv = P1[max(0, j - 30):j]
    lows = [x for x in pv if x[2] == ('lo' if s == 1 else 'hi')]; highs = [x for x in pv if x[2] == ('hi' if s == 1 else 'lo')]
    hl = None; neck = None; nfail = 0
    if len(lows) >= 2:
        l1, l2 = lows[-2], lows[-1]
        hl = s * (l2[3] - l1[3]) / a                                     # >0: higher low (buy) = fall failed
        mid = [x[3] for x in highs if l1[1] < x[1] < l2[1]]
        if mid:
            nk = max(mid) if s == 1 else min(mid); neck = s * (c1[k1] - nk) > 0
        # failed attempts: consecutive recent lows that did not break the lowest low of the prior leg
        base = min(x[3] for x in lows[-6:]) if s == 1 else max(x[3] for x in lows[-6:])
        nfail = sum(1 for x in lows[-4:] if s * (x[3] - base) >= -0.05 * a and x[3] != base)
    sl_now = s * (s75[k1] - s75[k1 - 10]) / a
    sl_prev = s * (s75[k1 - 10] - s75[k1 - 72]) / a
    k4 = bisect.bisect_right(C4, t) - 1; dd = 'up' if s == 1 else 'down'
    opp_recent = any(B.R1['bars'][k][0] not in (dd, None) and B.R1['bars'][k][0] != dd for k in range(max(0, k1 - 120), k1 + 1)) or \
        any(B.R4['bars'][k][0] not in (dd,) for k in range(max(0, k4 - 30), k4 + 1))
    fell = sl_prev < 0 or opp_recent
    typ = 'fail' if (fell and hl is not None and hl > 0) else ('pull' if sl_prev > 0 and B.R1['bars'][k1][0] == dd else 'other')
    rows.append(dict(time=p.time, side=s, typ=typ, hl=hl, neck=neck, nfail=nfail, sl_now=sl_now, sl_prev=sl_prev, fell=fell))
X = pd.DataFrame(rows)
print('分類:', X.typ.value_counts().to_dict())
print('  直前の安値(売りは高値)を切り上げ:', f"{(X.hl > 0).mean():.0%}", ' 中央', round(X.hl.median(), 2), 'ATR')
print('  ネックライン(2つの安値の間の高値)を超えている:', f"{X.neck.mean():.0%}")
print('  H1 SMA75 の傾き: 今(直近10本) 有利向き', f"{(X.sl_now > 0).mean():.0%}", '/ その前(10〜72本前) 不利向き', f"{(X.sl_prev < 0).mean():.0%}")
for ty in ('fail', 'pull', 'other'):
    g = X[X.typ == ty]
    if len(g):
        print(f'  [{ty}] {len(g)}件: 切り上げ{(g.hl > 0).mean():.0%} ネック超え{g.neck.mean():.0%} SMA75今有利{(g.sl_now > 0).mean():.0%} 前は不利{(g.sl_prev < 0).mean():.0%} 失敗回数中央{g.nfail.median():.0f}')
X.to_csv(B.HERE / 'results' / 'user_points_shape.csv', index=False)
print(X[X.typ == 'fail'].head(12).to_string())
