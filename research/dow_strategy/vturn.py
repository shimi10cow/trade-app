"""How often does a swing low/high turn without a lower-timeframe higher low (V-shape)? (2026-10-22)
For each confirmed H4 swing low (high mirrored): follow M15 from the low until price has risen 1 x ATR(H4). V-shape = no
M15 provisional up-turn (higher low) appeared before that. Also: share of H1 major up-turns that came with an M15
provisional turn in the 24h before. Run inside a pair workspace (DT_CACHE etc. set)."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from env_recognition.pivots import atr
h4 = B.h4.reset_index(drop=True); A4 = np.asarray(atr(h4)); T4 = pd.to_datetime(h4.t)
M15T = pd.to_datetime(B.T15); h, l = B.h, B.l
prov = [(e['idx'], e['to']) for e in B.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
pidx = {'up': sorted(i for i, d in prov if d == 'up'), 'down': sorted(i for i, d in prov if d == 'down')}
res = []
for e in B.R4['pivot_events']:
    if e['action'] != 'confirm':
        continue
    k = e['idx']; s = 1 if e['kind'] == 'lo' else -1; p = e['price']; a = A4[k]
    i0 = M15T.searchsorted(T4[k]); i1 = min(len(h), i0 + 16 * 4 * 10)   # look up to 10 days
    tgt = p + s * a; j = None
    for i in range(i0, i1):
        if (h[i] >= tgt) if s == 1 else (l[i] <= tgt):
            j = i; break
    if j is None:
        continue
    lst = pidx['up' if s == 1 else 'down']; q = bisect.bisect_left(lst, i0)
    had = q < len(lst) and lst[q] <= j
    res.append(dict(year=T4[k].year, side=s, v=not had, bars=j - i0))
D = pd.DataFrame(res); D = D[D.year >= 2005]
print(f"V字（M15の切り上げなしで1ATR戻す）の割合 {D.v.mean():.0%}（底 {D[D.side==1].v.mean():.0%} / 天井 {D[D.side==-1].v.mean():.0%}）, 1ATR戻すまでのM15本数 中央 {D.bars.median():.0f}, 件数 {len(D)}")
