"""Pair character 'ruler' (fixed 2026-10-21; used to pick an EA template for a new pair WITHOUT looking at EA results).
All on the pair's own bars 2005+, ATR(14) units of the same time frame, 24-bar horizon:
  turn_prov_H1 / turn_prov_M15 : move after a provisional turn made before the major trend turned (follow-through > 0 = turn follower)
  turn_major_H1 / turn_major_M15: move after a major reversal
  bo_cont_H4  : share of H4 major breakouts/reversals followed by another breakout (trend continues)
  retr_H1     : median H1 swing retracement vs the previous swing
  er200_H4    : median H4 efficiency ratio (200)
Writes results/character.json. Run inside each pair's workspace (DT_CACHE / DT_START as for the EAs)."""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
def atr(H, L, C, n=14):
    pc = np.r_[C[0], C[:-1]]; tr = np.maximum(H - L, np.maximum(abs(H - pc), abs(L - pc)))
    return pd.Series(tr).rolling(n).mean().to_numpy()
def follow(R, d, kind, h=24, lo=None, hi=None, se=False):
    H, L, C = (d[z].to_numpy(float) for z in 'hlc'); A = atr(H, L, C); n = len(C); out = []
    if kind == 'prov':
        ev = [(e['idx'], e['to']) for e in R['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and R['bars'][e['idx']][0] != e['to']]
    else:
        ev = [(e['idx'], e['to']) for e in R['events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL']
    for i, to in ev:
        ti = pd.Timestamp(d.t.iloc[i]) if 20 <= i < n else None
        if 20 <= i < n - h and np.isfinite(A[i]) and ti >= B.START and (lo is None or lo <= ti.year <= hi):
            out.append((1 if to == 'up' else -1) * (C[i + h] - C[i]) / A[i])
    if se:
        return float(np.mean(out)), float(np.std(out) / np.sqrt(len(out)))
    return float(np.mean(out)), len(out)
res = {}
for tf, R, d in (('H1', B.R1, B.h1), ('M15', B.R15, B.m15)):
    res[f'turn_prov_{tf}'], res[f'n_prov_{tf}'] = follow(R, d, 'prov')
    res[f'turn_major_{tf}'], res[f'n_major_{tf}'] = follow(R, d, 'major')
for tf, R, d in (('H1', B.R1, B.h1), ('M15', B.R15, B.m15)):
    for kind in ('prov', 'major'):
        m, e_ = follow(R, d, kind, se=True); a, _ = follow(R, d, kind, lo=2005, hi=2015); b, _ = follow(R, d, kind, lo=2016, hi=2026)
        res[f'turn_{kind}_{tf}_se'] = e_; res[f'turn_{kind}_{tf}_0515'] = a; res[f'turn_{kind}_{tf}_1626'] = b
ev = [e for e in B.R4['events'] if e.get('machine') == 'major' and e['action'] in ('BREAKOUT', 'REVERSAL')]
res['bo_cont_H4'] = float(np.mean([ev[i + 1]['action'] == 'BREAKOUT' for i in range(len(ev) - 1)]))
pv = sorted((e['idx'], e['price']) for e in B.R1['pivot_events'] if e.get('action', 'confirm') == 'confirm')
rr = [abs(c[1] - b[1]) / abs(b[1] - a[1]) for a, b, c in zip(pv, pv[1:], pv[2:]) if abs(b[1] - a[1]) > 0]
res['retr_H1'] = float(np.median(rr))
c4 = pd.Series(B.h4.c.to_numpy(float)); res['er200_H4'] = float((c4.diff(200).abs() / c4.diff().abs().rolling(200).sum()).median())
(B.HERE / 'results' / 'character.json').write_text(json.dumps(res, indent=1))
print(json.dumps({k: round(v, 3) for k, v in res.items()}, ensure_ascii=False))
