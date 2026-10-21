"""Pair chart fingerprint (2026-10-21), with entry-time focus. Run inside a pair's workspace (env as for the EAs).
Hour buckets in broker time (EET/EEST): 0-3 (late NY/early Asia), 3-7 (Tokyo morning), 7-10 (Tokyo/pre-London), 10-13 (London open),
13-16 (London/NY overlap start), 16-19 (NY), 19-24 (NY afternoon/late).
Writes results/fingerprint.json and prints tables."""
import sys, json, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
import env_ctx as EC  # noqa: E402
B = X.B
BK = [(0, 3), (3, 7), (7, 10), (10, 13), (13, 16), (16, 19), (19, 24)]
def bucket(h):
    for a, b in BK:
        if a <= h < b: return f'{a}-{b}'
m15 = B.m15; T15 = pd.DatetimeIndex(B.T15); O, H, L, C = (m15[z].to_numpy(float) for z in 'ohlc'); N = len(C)
CL15 = X.CL15; A1 = B.A1; C1 = np.array(B.C1, dtype='datetime64[ns]')
K1 = np.clip(np.searchsorted(C1, CL15.to_numpy(), side='right') - 1, 0, len(C1) - 1)
start = CL15.searchsorted(B.START)
hrs = T15.hour.to_numpy(); bk = np.array([bucket(h) for h in hrs])
a1 = A1[K1]
out = {}
# A. activity: |M15 move| / ATR(H1) by bucket, and share of the day's total |move|
mv = np.abs(C - O) / a1; ok = np.arange(N) >= start
act = pd.Series(mv[ok]).groupby(bk[ok]).mean(); out['activity'] = act.round(3).to_dict()
tot = pd.Series(np.abs(C - O)[ok]).groupby(bk[ok]).sum(); out['move_share'] = (tot / tot.sum()).round(3).to_dict()
# F. noise: wick share of the M15 range
rng = H - L; wick = np.where(rng > 0, (rng - np.abs(C - O)) / np.where(rng > 0, rng, 1), np.nan)
out['wick_share_M15'] = round(float(np.nanmean(wick[ok])), 3)
h1 = B.h1; r1 = (h1.h - h1.l).to_numpy(); w1 = np.where(r1 > 0, (r1 - np.abs(h1.c - h1.o).to_numpy()) / np.where(r1 > 0, r1, 1), np.nan)
out['wick_share_H1'] = round(float(np.nanmean(w1)), 3)
# forward move helper
def fwd(i, s, h):
    return s * (C[min(i + h, N - 1)] - C[i]) / a1[i]
# B. follow-through by bucket: H1 breakout (major BREAKOUT) and M15 provisional turn (+H4 prov same)
M15_OF_H1 = np.clip(CL15.searchsorted(pd.DatetimeIndex(B.C1)), 0, N - 1)
h1maj = [b[0] for b in B.R1['bars']]; C4 = np.array(B.C4, dtype='datetime64[ns]'); h4p = [b[0] for b in B.R4['prov_bars']]
rows = []
for e in B.R1['events']:
    if e.get('machine') == 'major' and e['action'] == 'BREAKOUT':
        i = M15_OF_H1[e['idx']]; d = h1maj[e['idx']]
        if i >= start and d in ('up', 'down') and i + 96 < N:
            s = 1 if d == 'up' else -1
            # fake: an H1 close back beyond the broken level within 4 H1 bars  (level ~ close before the breakout bar)
            k = e['idx']; lvl = B.h1.c.iloc[k - 1] if k > 0 else np.nan
            fake = any(s * (B.h1.c.iloc[k + j] - lvl) < 0 for j in range(1, 5) if k + j < len(B.h1))
            rows.append(dict(kind='bo_h1', b=bk[i], f24=fwd(i, s, 24), f96=fwd(i, s, 96), fake=fake))
for e in B.R15['prov_events']:
    if e['action'] not in ('REVERSAL', 'PROV_START'): continue
    i = e['idx']; to = e['to']
    if i < start or i + 96 >= N or B.R15['bars'][i][0] == to: continue
    k4 = np.searchsorted(C4, CL15[i].to_datetime64(), side='right') - 1
    if k4 < 0 or h4p[k4] != to: continue
    s = 1 if to == 'up' else -1
    rows.append(dict(kind='turn_m15_h4', b=bk[i], f24=fwd(i, s, 24), f96=fwd(i, s, 96), fake=np.nan))
F = pd.DataFrame(rows)
g = F.groupby(['kind', 'b']).agg(n=('f24', 'size'), f24=('f24', 'mean'), f96=('f96', 'mean'), fake=('fake', 'mean')).round(3)
out['follow'] = {f'{k}|{b}': v for (k, b), v in g.to_dict('index').items()}
# D. pullback depth (H1 swing retracement quantiles) and E. reaction at H1 SMA75 in a trend
pv = sorted((e['idx'], e['price']) for e in B.R1['pivot_events'] if e.get('action', 'confirm') == 'confirm')
rr = np.array([abs(c[1] - b[1]) / abs(b[1] - a[1]) for a, b, c in zip(pv, pv[1:], pv[2:]) if abs(b[1] - a[1]) > 0])
out['retr_q'] = {q: round(float(np.quantile(rr, q)), 2) for q in (0.25, 0.5, 0.75)}
h1c = B.h1.c.to_numpy(float); h1l = B.h1.l.to_numpy(float); h1h = B.h1.h.to_numpy(float); S75 = pd.Series(h1c).rolling(75).mean().to_numpy()
bounce = []
for k in range(200, len(h1c) - 24):
    if pd.Timestamp(B.C1[k]) < B.START: continue
    d = h1maj[k]
    if d == 'up' and h1l[k] <= S75[k] < h1c[k]: bounce.append((bucket((pd.Timestamp(B.C1[k]) - pd.Timedelta(hours=1)).hour), (h1c[k + 24] - h1c[k]) / A1[k]))
    if d == 'down' and h1h[k] >= S75[k] > h1c[k]: bounce.append((bucket((pd.Timestamp(B.C1[k]) - pd.Timedelta(hours=1)).hour), -(h1c[k + 24] - h1c[k]) / A1[k]))
bo = pd.DataFrame(bounce, columns=['b', 'f']); out['ma75_bounce'] = {'all': round(bo.f.mean(), 3), 'win': round((bo.f > 0).mean(), 3), **bo.groupby('b').f.mean().round(3).to_dict()}
# G. range time
rs = EC._RS; out['range_time'] = round(float(np.nanmean(rs[-len(rs) // 2:] > 0.7)), 3) if rs is not None else None
# H. EA results by entry-hour bucket
F_EA = {'R': 'regime2_R2c.csv', 'T': 'regime2_T1t.csv', 'L': 'tl_N2.csv', 'A': 'retest_N1.csv', 'C': 'step2/cl15_md4tri.csv',
        'J2': 'turn/jt2_h1major+hour0_10.csv', 'J3': 'turn/j3_h41_s0_h1prot.csv', 'J': 'turn/jt2_h1major.csv'}
ea = {}
for c, f in F_EA.items():
    p = B.HERE / 'results' / f
    if not p.exists(): continue
    d = pd.read_csv(p)
    t = pd.to_datetime(d.time) if 'Rc' in d else pd.to_datetime(d.t); R = d.Rc if 'Rc' in d else d.R
    m = t.dt.year >= 2005; t = t[m]; R = R[m]
    g = pd.DataFrame(dict(b=[bucket(h) for h in t.dt.hour], R=R, y=t.dt.year))
    ea[c] = {b: dict(n=int(len(x)), R=round(x.R.sum(), 1), PF=round(x.R[x.R > 0].sum() / max(1e-9, -x.R[x.R <= 0].sum()), 2),
                     R1=round(x.R[x.y <= 2015].sum(), 1), R2=round(x.R[x.y >= 2016].sum(), 1)) for b, x in g.groupby('b')}
out['ea_by_hour'] = ea
(B.HERE / 'results' / 'fingerprint.json').write_text(json.dumps(out, indent=1, default=float))
print(json.dumps({k: v for k, v in out.items() if k not in ('follow', 'ea_by_hour')}, ensure_ascii=False))
print(g.to_string() if False else pd.DataFrame(out['follow']).T.to_string())
