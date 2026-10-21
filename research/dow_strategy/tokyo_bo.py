"""Tokyo-range breakout in London (JST), as a trade (2026-10-21). Same settings on every pair.
Tokyo range = JST 9:00-15:00 high/low. From 15:00 to 21:00, the first M15 close beyond the range by >= f x ATR(D) -> enter at the
next M15 open in that direction (one trade per day). Stop: the middle of the Tokyo range (or the opposite side). Exit: JST 24:00
(time exit) or trail variants. Cost 1.2 pip. Halves reported."""
import os, sys
import numpy as np, pandas as pd
m = pd.read_csv(os.environ['EA_M15_CACHE'], parse_dates=['time'])
t = m.time.dt.tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').dt.tz_convert('Asia/Tokyo').dt.tz_localize(None)
m = m.assign(jt=t).dropna(subset=['jt']); m = m[m.jt >= '2004-12-01'].reset_index(drop=True)
m['d'] = m.jt.dt.normalize(); m['h'] = m.jt.dt.hour + m.jt.dt.minute / 60
dly = m.groupby('d').agg(hi=('high', 'max'), lo=('low', 'min'), cl=('close', 'last'))
pc = dly.cl.shift(1); tr = np.maximum(dly.hi - dly.lo, np.maximum(abs(dly.hi - pc), abs(dly.lo - pc))); atrD = tr.rolling(14).mean().shift(1)
O, H, L, C = (m[z].to_numpy(float) for z in ('open', 'high', 'low', 'close')); HH = m.h.to_numpy(); DD = m.d.to_numpy()
idx = {d: np.nonzero(DD == d)[0] for d in np.unique(DD)}
COST = 1.2e-4
def run(f=0.0, stop='mid', exit_h=24.0, maxrng=9.0):
    res = []
    for d, ii in idx.items():
        if pd.Timestamp(d).year < 2005: continue
        a = atrD.get(pd.Timestamp(d), np.nan)
        if not np.isfinite(a): continue
        tk = ii[(HH[ii] >= 9) & (HH[ii] < 15)]; ld = ii[(HH[ii] >= 15) & (HH[ii] < 21)]
        if len(tk) < 20 or len(ld) < 20: continue
        TH, TL = H[tk].max(), L[tk].min()
        if (TH - TL) / a > maxrng: continue
        for i in ld:
            s = 1 if C[i] > TH + f * a else (-1 if C[i] < TL - f * a else 0)
            if s == 0: continue
            if i + 1 >= len(C): break
            e = O[i + 1]; sl = (TH + TL) / 2 if stop == 'mid' else (TL if s == 1 else TH)
            risk = s * (e - sl)
            if risk <= 3e-4: break
            R = None; j = i + 1
            while j < len(C) and (DD[j] == d and HH[j] < exit_h or (exit_h > 24 and DD[j] != d and HH[j] < exit_h - 24)):
                if (L[j] <= sl) if s == 1 else (H[j] >= sl): R = -1.0; break
                j += 1
            if R is None: R = s * (C[min(j - 1, len(C) - 1)] - e) / risk
            res.append((pd.Timestamp(d), R - COST / risk, risk, (TH - TL) / a)); break
    return pd.DataFrame(res, columns=['d', 'R', 'risk', 'rng'])
def pf(r): w = r > 0; return r[w].sum() / max(1e-9, -r[~w].sum())
def line(lab, x):
    r = x.R.to_numpy(); y = x.d.dt.year.to_numpy()
    print(f'{lab:34s} n={len(r):4d} {r.sum():+7.1f}R PF{pf(r):.2f} 勝率{(r > 0).mean():.0%} | 前半 {r[y <= 2015].sum():+.1f}R PF{pf(r[y <= 2015]):.2f} | 後半 {r[y >= 2016].sum():+.1f}R PF{pf(r[y >= 2016]):.2f} | 損切り中央{np.median(x.risk) / 1e-4:.0f}p', flush=True)
line('抜けで入る・損切り中央・24時決済', run())
line('0.1ATR抜け・損切り中央・24時', run(f=0.1))
line('抜けで入る・損切り反対側・24時', run(stop='opp'))
line('抜けで入る・損切り中央・翌2時', run(exit_h=26))
line('東京レンジ狭い日(<0.5)だけ', run(maxrng=0.5))
