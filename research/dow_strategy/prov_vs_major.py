"""User: 'USDJPY decides the turn with a higher low before breaking the lower high'. Check per pair (H1, M15):
for each provisional turn (higher low after a down trend, mirrored): does a major reversal follow (within 120 bars, before
the provisional turn flips back)? how far price has already moved (ATR) from the provisional turn to the major confirmation,
and what follows after each point (next 24/72 bars, ATR, in the turn direction)."""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
def atr(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]; tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n).mean().to_numpy()
import sys, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402  (run with each pair's DT_CACHE / workspace)
p = os.environ.get('PAIR_LABEL', 'EUR')
for tf, R, d in (('H1', B.R1, B.h1), ('M15', B.R15, B.m15)):
        H, L, C = (d[z].to_numpy(float) for z in 'hlc'); A = atr(H, L, C); n = len(C)
        prov = [(e['idx'], e['to']) for e in R['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
        maj = {}
        for e in R['events']:
            if e.get('machine') == 'major' and e['action'] == 'REVERSAL':
                maj.setdefault(e['to'], []).append(e['idx'])
        maj = {k: np.array(sorted(v)) for k, v in maj.items()}
        pv_idx = {k: np.array(sorted(i for i, t in prov if t == k)) for k in ('up', 'down')}
        rows = []
        for i, to in prov:
            if i + 72 >= n or i < 20 or R['bars'][i][0] == to:
                continue                                     # only provisional turns made BEFORE the major trend turned
            s = 1 if to == 'up' else -1; opp = 'down' if to == 'up' else 'up'
            # next opposite provisional turn ends this attempt
            po = pv_idx[opp]; k = np.searchsorted(po, i + 1); end = po[k] if k < len(po) else n - 1
            mj = maj.get(to, np.array([], int)); j = np.searchsorted(mj, i)
            confirmed = j < len(mj) and mj[j] <= min(end, i + 120)
            a = A[i]
            row = dict(conf=confirmed, f24=s * (C[min(i + 24, n - 1)] - C[i]) / a, f72=s * (C[min(i + 72, n - 1)] - C[i]) / a)
            if confirmed:
                im = mj[j]; row.update(lag=im - i, moved=s * (C[im] - C[i]) / a, m24=s * (C[min(im + 24, n - 1)] - C[im]) / a)
            rows.append(row)
        X = pd.DataFrame(rows); cf = X[X.conf]
        print(f'{p} {tf}: 仮転換 {len(X)}回 → 本転換になった {X.conf.mean():.0%} | 仮→本 までに {cf.lag.median():.0f}本・既に {cf.moved.median():+.1f}ATR 動いている'
              f' | その後24本: 仮転換で入る {X.f24.mean():+.2f}ATR / 本転換で入る {cf.m24.mean():+.2f}ATR')
