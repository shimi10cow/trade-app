"""Among all pullback setups (pb_ea counter, n<=3) in the marked years, which did the user mark? Compare features.
Usage (USDJPY workspace): MARKS=<marks_all.pkl> python dow_strategy/pb_marked_vs_not.py"""
import sys, os, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pb_ea as P  # noqa: E402
B = P.B
M = pd.read_pickle(os.environ['MARKS']); M = M[M.tf == 'H1']; M['tt'] = pd.to_datetime(M.t, unit='s')
h4 = B.h4.reset_index(drop=True); c4 = h4.c
from env_recognition.pivots import atr
A4 = np.asarray(atr(h4)); m4_20 = c4.rolling(20).mean().to_numpy(); m4_75 = c4.rolling(75).mean().to_numpy()
P4 = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R4['prov_bars']]
J4 = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R4['bars']]
st = P.counter(2.0)
rows = []; last_reset = 0; prev_side = 0
for i, (s, n, armed, new) in enumerate(st):
    if s != prev_side or (i and st[i - 1][1] > n):
        last_reset = i
    prev_side = s
    if not new or s == 0 or n + 1 > 3:
        continue
    t = P.CL[i]
    if t.year not in (2010, 2019, 2026):
        continue
    k4 = bisect.bisect_right(B.C4, t) - 1
    mk = M[(M.side == s) & ((M.tt - t).abs() <= pd.Timedelta(hours=12))]
    vol = P.A1[i] / np.nanmedian(P.A1[max(0, i - 500):i + 1])
    rows.append(dict(t=t, year=t.year, side=s, num=n + 1, marked=len(mk) > 0,
                     h1ma=int(np.sign(P.M20[i] - P.M75[i]) * s), h1maj=P.MAJ[i] * s,
                     h1d75=s * (P.cc[i] - P.M75[i]) / P.A1[i], h1d20=s * (P.cc[i] - P.M20[i]) / P.A1[i],
                     h4ma=int(np.sign(m4_20[k4] - m4_75[k4]) * s), h4prv=P4[k4] * s, h4maj=J4[k4] * s,
                     h4d75=s * (c4[k4] - m4_75[k4]) / A4[k4], bars=i - last_reset, vol=vol,
                     jst=(t.hour + 7) % 24))
D = pd.DataFrame(rows)
print('setups', len(D), 'marked', D.marked.sum(), D.groupby('year').marked.agg(['size', 'sum']).to_dict())
pd.set_option('display.width', 200)
for c in ['num', 'h1ma', 'h1maj', 'h4ma', 'h4prv', 'h4maj']:
    print(c, D.groupby(c).marked.agg(['size', 'mean']).round(2).T.to_dict())
for c in ['h1d75', 'h1d20', 'h4d75', 'bars', 'vol']:
    q = pd.qcut(D[c], 4, duplicates='drop'); print(c, D.groupby(q, observed=True).marked.agg(['size', 'mean']).round(2).to_dict('index'))
print('jst', D.groupby(pd.cut(D.jst, [-1, 5, 8, 14, 17, 20, 23])).marked.agg(['size', 'mean']).round(2).to_dict('index'))
D.to_csv(B.HERE / 'results' / 'pb' / 'marked_vs_not.csv', index=False)
