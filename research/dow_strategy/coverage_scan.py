"""Which existing USDJPY variant catches the user's marks? (2026-10-22)
For every trade file: share of marks (same side, entry within 12h of the mark) by mark type, separately for the 2010 marks
(design, first half) and the 2019 + 2026 marks (check), plus first/second-half R and PF."""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
RD = Path('/home/user/trade-app/research/dow_strategy/results/usdjpy')
M = pd.read_pickle(f'{S}/tdiag/marks_all.pkl'); M = M[M.tf == 'H1'].copy()
M['lab'] = M.label.replace({'3': '3+', '4': '3+', 'rev': 'bo'}); M['tt'] = pd.to_datetime(M.t, unit='s')
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
rows = []
for f in sorted(RD.rglob('*.csv')):
    rel = str(f.relative_to(RD))
    try:
        d = pd.read_csv(f)
    except Exception:
        continue
    if 'Rc' in d and 'time' in d: t, R = pd.to_datetime(d.time), d.Rc
    elif 'R' in d and 't' in d and 'side' in d: t, R = pd.to_datetime(d.t), d.R
    else: continue
    if len(d) < 50: continue
    tv = t.values.astype('datetime64[ns]'); sd = d.side.to_numpy()
    hit = []
    for m in M.itertuples():
        w = np.abs((tv - np.datetime64(m.tt)) / np.timedelta64(1, 'h')) <= 12
        hit.append(bool(((sd == m.side) & w).any()))
    M['hit'] = hit; y = t.dt.year
    a = R[(y >= 2005) & (y <= 2015)]; b = R[y >= 2016]
    r = dict(file=rel, n_yr=len(R[y >= 2005]) / 22, a=a.sum(), pa=pf(a), b=b.sum(), pb=pf(b))
    for yrs, tag in (([2010], 'd'), ([2019, 2026], 'c')):
        g = M[M.year.isin(yrs)]
        r[f'{tag}_all'] = g.hit.mean()
        for lab in ('1', '2', '3+', 'bo'): r[f'{tag}_{lab}'] = g[g.lab == lab].hit.mean()
    rows.append(r)
T = pd.DataFrame(rows); T.to_csv(f'{S}/feat/coverage_scan_usdjpy.csv', index=False)
print(len(T), 'files')
print('前半の印（2010）拾い率と、後半の印（2019・2026）拾い率の相関', round(T.d_all.corr(T.c_all), 2))
c = T[(T.pa >= 1.1) & (T.a > 0)].sort_values('d_all', ascending=False)
pd.set_option('display.width', 250)
print('前半 PF1.1 以上の中で、2010 の印を多く拾う順（上位 15）')
print(c[['file', 'n_yr', 'a', 'pa', 'b', 'pb', 'd_all', 'd_1', 'd_2', 'd_bo', 'c_all', 'c_1', 'c_2', 'c_bo']].head(15).round(2).to_string(index=False))
