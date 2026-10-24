"""TF (early-Tokyo fade) robustness: by JST entry hour, excluding the rollover hour (broker 23:00-00:59), and with higher costs.
k=1.5, target 50%, stop impulse extreme + 0.2 ATR(H1), hold 8 M15 bars."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import session_ea as SE  # noqa: E402  (frames; also re-runs EV/TF prints - fine)
T15, O, H, L, C, N, a1, JST = SE.T15, SE.O, SE.H, SE.L, SE.C, SE.N, SE.a1, SE.JST
BH = T15.hour.to_numpy()
def run(k=1.5, hold=8, cost=1.2e-4, hours=(6, 7, 8), no_roll=False, spread_pad=0.0):
    res = []; i = 4; busy = -1
    while i < N - hold - 1:
        if JST[i] not in hours or i <= busy or not a1[i] > 0 or (no_roll and (BH[i] == 23 or BH[i] == 0 or BH[i + 1] == 0)):
            i += 1; continue
        mv = (C[i] - C[i - 4]) / a1[i]
        if abs(mv) < k:
            i += 1; continue
        s = -1 if mv > 0 else 1; e = O[i + 1]; ext = H[i - 3:i + 1].max() if s == -1 else L[i - 3:i + 1].min()
        sl = ext - s * 0.2 * a1[i]; risk = s * (e - sl)
        if risk <= 2e-4:
            i += 1; continue
        tp = e + s * 0.5 * abs(C[i] - C[i - 4]); R = None
        for j in range(i + 1, i + 1 + hold):
            if (L[j] <= sl) if s == 1 else (H[j] >= sl): R = -1.0; break
            if (H[j] >= tp) if s == 1 else (L[j] <= tp): R = s * (tp - e) / risk; break
        if R is None: R = s * (C[i + hold] - e) / risk; j = i + hold
        res.append((T15[i + 1], R - cost / risk, risk)); busy = j; i = j + 1
    return pd.DataFrame(res, columns=['t', 'R', 'risk'])
def line(lab, d):
    d = d[d.t.dt.year >= 2005]; r = d.R.to_numpy(); y = d.t.dt.year.to_numpy()
    pf = lambda x: x[x > 0].sum() / max(1e-9, -x[x <= 0].sum())
    print(f'{lab:28s} n={len(r):4d} {r.sum():+6.1f}R PF{pf(r):.2f} 前半PF{pf(r[y <= 2015]):.2f} 後半PF{pf(r[y >= 2016]):.2f} 損切り中央{np.median(d.risk) / 1e-4:.1f}p', flush=True)
print('---- TF robustness')
line('基準 6-9時 cost1.2', run())
for h in (6, 7, 8):
    line(f'{h}時台だけ', run(hours=(h,)))
line('ロールオーバー除外', run(no_roll=True))
line('ロールオーバー除外 cost2.0', run(no_roll=True, cost=2.0e-4))
line('ロールオーバー除外 cost3.0', run(no_roll=True, cost=3.0e-4))
line('ロールオーバー除外 7-9時', run(no_roll=True, hours=(7, 8)))
