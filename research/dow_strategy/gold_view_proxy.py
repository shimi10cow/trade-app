"""Gold: find a causal state that imitates the user's H4 trend view (marks 2013 / 2019), then use it as a 'do not trade
against it' filter on the gold EAs over 20 years (2026-10-23). Run inside the XAUUSD workspace.
Candidates (each gives +1 / -1 at every H4 close, using only the past):
  dow4M / dow4P / dow1M / dow1P : H4 / H1 major or provisional Dow trend
  ma{n}s : slope of H4 SMA n (n = 20, 50, 75) over 5 bars;  ma{n}p : H4 close above / below SMA n
  dc{n}  : H4 Donchian state (close above the last n-bar high -> up, below the n-bar low -> down), n = 10, 20
  combos : dow4P & ma20s agree (else keep previous), dow4P & ma50p agree
Fit = agreement with the user's non-range state on 2013 H4 bars; check = 2019."""
import sys, json, glob
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
M = pd.DataFrame([json.load(open(f)) for f in glob.glob(f'{S}/gold_marks/pbmarks/*.json')]); M['tm'] = pd.to_datetime(M.t, unit='s'); M = M.sort_values('tm')
st = []; cur = 0
for x in M.itertuples():
    cur = int(x.side) if x.kind == 'B' else 0 if x.kind == 'R' else cur; st.append((x.tm, cur))
U = pd.Series([s for _, s in st], index=pd.DatetimeIndex([t for t, _ in st]))
h4 = B.h4.reset_index(drop=True); C4 = pd.DatetimeIndex(B.C4); c = h4.c.to_numpy(float); hi = h4.h.to_numpy(float); lo = h4.l.to_numpy(float)
sgn = lambda a: np.where(a > 0, 1, np.where(a < 0, -1, 0))
P = {}
P['dow4M'] = np.array([{'up': 1, 'down': -1}.get(b[0], 0) for b in B.R4['bars']])
P['dow4P'] = np.array([{'up': 1, 'down': -1}.get(b[0], 0) for b in B.R4['prov_bars']])
C1 = pd.DatetimeIndex(B.C1); k1 = np.clip(C1.searchsorted(C4, 'right') - 1, 0, len(C1) - 1)
P['dow1M'] = np.array([{'up': 1, 'down': -1}.get(b[0], 0) for b in B.R1['bars']])[k1]
P['dow1P'] = np.array([{'up': 1, 'down': -1}.get(b[0], 0) for b in B.R1['prov_bars']])[k1]
for n in (20, 50, 75):
    ma = pd.Series(c).rolling(n).mean().to_numpy(); P[f'ma{n}s'] = sgn(ma - np.roll(ma, 5)); P[f'ma{n}p'] = sgn(c - ma)
for n in (10, 20):
    hh = pd.Series(hi).rolling(n).max().shift(1).to_numpy(); ll = pd.Series(lo).rolling(n).min().shift(1).to_numpy(); s_ = np.zeros(len(c)); v = 0
    for i in range(len(c)):
        v = 1 if c[i] > hh[i] else -1 if c[i] < ll[i] else v; s_[i] = v
    P[f'dc{n}'] = s_.astype(int)
def combo(a, b):
    out = np.zeros(len(a), int); v = 0
    for i in range(len(a)):
        if a[i] == b[i] and a[i] != 0: v = a[i]
        out[i] = v
    return out
P['P&ma20s'] = combo(P['dow4P'], P['ma20s']); P['P&ma50p'] = combo(P['dow4P'], P['ma50p']); P['P&dc10'] = combo(P['dow4P'], P['dc10'])
iu = U.index.searchsorted(C4, 'right') - 1; uv = np.where(iu >= 0, U.to_numpy()[np.maximum(iu, 0)], np.nan)
rows = []
for k, a in P.items():
    r = dict(判定=k)
    for y in (2013, 2019):
        m = (C4.year == y) & (uv != 0) & ~np.isnan(uv); yy = C4.year == y
        r[f'一致{y}'] = (a[m] == uv[m]).mean(); r[f'切替{y}'] = int((np.diff(a[yy]) != 0).sum())
    rows.append(r)
D = pd.DataFrame(rows).sort_values('一致2013', ascending=False)
print('ユーザーの切り替え 2013: 21回 / 2019: 26回'); print(D.round(3).to_string(index=False))
pd.DataFrame({k: v for k, v in P.items()}, index=C4).to_pickle(f'{S}/feat/gold_proxies.pkl')
