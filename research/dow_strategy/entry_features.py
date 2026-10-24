"""State at each trade's entry, for the feedback-derived skip rules (2026-10-22). Run inside a pair workspace.
For every trade of the listed EA files: (1) H4 overextension = distance of the H4 close from H4 SMA75 in ATR(H4), and the
H4 push count since the H4 SMA20/75 cross; (2) H1 provisional / major Dow against the trade; (3) room to the nearest
opposing H4 swing (buy: last confirmed H4 high above the entry) in ATR(H1); (4) H4 range score; (5) M15 provisional Dow
against the trade. Only information known at the signal bar's close is used.
Usage: python entry_features.py <results dir> <out csv> [extra code:file ...]"""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
import env_ctx as EC  # noqa: E402
from gen_pbcount import Pushes  # noqa: E402
from env_recognition.pivots import atr
RD = Path(sys.argv[1]); OUTF = sys.argv[2]
SRC = [('R', 'regime2_R2c.csv'), ('T', 'regime2_T1t.csv'), ('L', 'tl_N2.csv'), ('A', 'retest_N1.csv'), ('C', 'step2/cl15_md4tri.csv'),
       ('J2', 'turn/jt2_h1major+hour0_10.csv'), ('J3', 'turn/j3_h41_s0_h1prot.csv'), ('EV', 'session/ev_18-21+0-3.csv'), ('P', 'pb/P4_maj0_rs0.5.csv')]
SRC += [tuple(a.split(':', 1)) for a in sys.argv[3:]]
h4 = B.h4.reset_index(drop=True); h1 = B.h1.reset_index(drop=True)
C4 = np.array(B.C4, dtype='datetime64[ns]'); C1 = np.array(B.C1, dtype='datetime64[ns]')
A4 = np.asarray(atr(h4)); A1 = np.asarray(B.A1)
m4_20 = h4.c.rolling(20).mean().to_numpy(); m4_75 = h4.c.rolling(75).mean().to_numpy(); c4 = h4.c.to_numpy()
side = lambda bars: np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in bars])
P1 = side(B.R1['prov_bars']); J1 = side(B.R1['bars']); P15 = side(B.R15['prov_bars']); P4 = side(B.R4['prov_bars'])
conf4 = {}
for e in B.R4['pivot_events']:
    if e['action'] == 'confirm': conf4.setdefault(e['available_idx'], []).append(e)
ma4 = np.sign(m4_20 - m4_75); ma4[~np.isfinite(ma4)] = 0
PU = Pushes(); push4 = np.array([PU.step(i, int(ma4[i]), h4.h[i], h4.l[i], conf4.get(i, []))[1] for i in range(len(h4))])
piv4 = sorted(((B.C4[e['available_idx']], e['kind'], e['price']) for e in B.R4['pivot_events'] if e['action'] == 'confirm'), key=lambda x: x[0])
PT4 = np.array([p[0] for p in piv4], dtype='datetime64[ns]')
T15 = np.array(B.T15 + pd.Timedelta(minutes=15), dtype='datetime64[ns]')
rows = []
for code, f in SRC:
    p = RD / f
    if not p.exists(): continue
    d = pd.read_csv(p)
    if 'Rc' in d: t, R = pd.to_datetime(d.time), d.Rc
    else: t, R = pd.to_datetime(d.t), d.R
    for ti, s, e, r, rk in zip(t, d.side, d.entry, R, d.risk):
        tt = np.datetime64(ti)
        k4 = np.searchsorted(C4, tt, 'right') - 1; k1 = np.searchsorted(C1, tt, 'right') - 1; k15 = np.searchsorted(T15, tt, 'right') - 1
        if min(k4, k1, k15) < 0: continue
        # nearest opposing H4 swing confirmed before entry
        j = np.searchsorted(PT4, tt, 'right') - 1; room = np.nan; seen = 0
        while j >= 0 and seen < 60:
            tm, kind, pr = piv4[j]
            if (kind == 'hi' and s == 1 and pr > e) or (kind == 'lo' and s == -1 and pr < e):
                room = abs(pr - e) / A1[k1]; break
            j -= 1; seen += 1
        x = EC.ctx_at(ti, s)
        rows.append(dict(ea=code, t=ti, side=s, R=r, risk=rk, year=ti.year,
                         h4_d75=s * (c4[k4] - m4_75[k4]) / A4[k4], h4_push=push4[k4] if ma4[k4] == s else -1,
                         h4_prov_against=int(P4[k4] == -s), h1_prov_against=int(P1[k1] == -s), h1_major_against=int(J1[k1] == -s),
                         m15_prov_against=int(P15[k15] == -s), room_h4=room, rs=x['rs']))
D = pd.DataFrame(rows); D.to_csv(OUTF, index=False); print(len(D), 'trades ->', OUTF)
