"""H1 wave shape and H4 trend progress at each trade's entry (user, 2026-10-22: 'time axis' of the correction).
Impulse = last confirmed H1 swing in the trade direction back to the opposite swing before it (buy: low -> high).
Correction = from that high to the entry. Features (all known at entry):
  t_ratio  = correction hours / impulse hours      (has the correction taken time? 'the time axis is filled')
  p_ratio  = correction depth / impulse size       (retracement)
  angle    = correction depth per hour in ATR(H1)  (steep vs flat correction)
  ma_gap   = |close - H1 SMA20| / ATR(H1), ma_slope = |SMA20 change over 10 bars| / ATR(H1)  (has the MA caught up?)
  h4_major_push = new extremes made after confirmed pullbacks since the H4 major Dow turn (how far the H4 trend has run)
  imp_atr  = impulse size in ATR(H1)
Run inside a pair workspace. Usage: python wave_features.py <results dir> <out csv> [code:file ...]"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from gen_pbcount import Pushes  # noqa: E402
RD = Path(sys.argv[1]); OUTF = sys.argv[2]
SRC = [('R', 'regime2_R2c.csv'), ('T', 'regime2_T1t.csv'), ('L', 'tl_N2.csv'), ('A', 'retest_N1.csv'), ('C', 'step2/cl15_md4tri.csv'),
       ('J2', 'turn/jt2_h1major+hour0_10.csv'), ('J3', 'turn/j3_h41_s0_h1prot.csv'), ('EV', 'session/ev_18-21+0-3.csv'), ('P', 'pb/P4_maj0_rs0.5.csv')]
SRC += [tuple(a.split(':', 1)) for a in sys.argv[3:]]
h1 = B.h1.reset_index(drop=True); h4 = B.h4.reset_index(drop=True)
T1 = pd.to_datetime(h1.t).to_numpy(); C1 = np.array(B.C1, dtype='datetime64[ns]'); C4 = np.array(B.C4, dtype='datetime64[ns]')
A1 = np.asarray(B.A1); c1 = h1.c.to_numpy(); m20 = h1.c.rolling(20).mean().to_numpy()
# H1 confirmed pivots with anchor bar and confirmation time
P = sorted(((B.C1[e['available_idx']], e['kind'], e['price'], e['idx']) for e in B.R1['pivot_events'] if e['action'] == 'confirm'), key=lambda x: x[0])
PT = np.array([p[0] for p in P], dtype='datetime64[ns]')
# H4 pushes since the H4 major turn
conf4 = {}
for e in B.R4['pivot_events']:
    if e['action'] == 'confirm': conf4.setdefault(e['available_idx'], []).append(e)
maj4 = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R4['bars']]
PU = Pushes(); st4 = [PU.step(i, maj4[i], h4.h[i], h4.l[i], conf4.get(i, [])) for i in range(len(h4))]
rows = []
for code, f in SRC:
    p = RD / f
    if not p.exists(): continue
    d = pd.read_csv(p)
    if 'Rc' in d: t, R = pd.to_datetime(d.time), d.Rc
    else: t, R = pd.to_datetime(d.t), d.R
    for ti, s, e, r, rk in zip(t, d.side, d.entry, R, d.risk):
        tt = np.datetime64(ti); k1 = np.searchsorted(C1, tt, 'right') - 1; k4 = np.searchsorted(C4, tt, 'right') - 1
        if k1 < 80 or k4 < 0: continue
        j = np.searchsorted(PT, tt, 'right') - 1
        want = 'hi' if s == 1 else 'lo'
        while j >= 0 and P[j][1] != want: j -= 1
        if j < 1: continue
        ext_p, ext_i = P[j][2], P[j][3]
        jj = j - 1
        while jj >= 0 and P[jj][1] == want: jj -= 1
        if jj < 0: continue
        org_p, org_i = P[jj][2], P[jj][3]
        imp = s * (ext_p - org_p); imp_h = max(1, ext_i - org_i); cor_h = max(1, k1 - ext_i)
        if imp <= 0: continue
        depth = s * (ext_p - e)
        sd, n4 = st4[k4]
        rows.append(dict(ea=code, t=ti, side=s, R=r, risk=rk, year=ti.year,
                         t_ratio=cor_h / imp_h, p_ratio=depth / imp, angle=max(depth, 0) / cor_h / A1[k1], imp_atr=imp / A1[k1],
                         cor_h=cor_h, imp_h=imp_h, ma_gap=abs(c1[k1] - m20[k1]) / A1[k1], ma_slope=abs(m20[k1] - m20[k1 - 10]) / A1[k1],
                         h4_major_push=(n4 if sd == s else -1)))
D = pd.DataFrame(rows); D.to_csv(OUTF, index=False); print(len(D), 'trades ->', OUTF)
