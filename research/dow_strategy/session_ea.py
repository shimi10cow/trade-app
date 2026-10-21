"""Two session EAs from the JST session study (2026-10-21), identical settings on every pair.
EV (evening turn follower): the turn follower J (M15 provisional turn before the major, H4 provisional same, stop beyond
   the higher low + 0.3 ATR(H1), H1 trail from +1R) but only for turns in JST 18-21 (variants: 18-24, 18-21 + 0-3).
TF (early-Tokyo fade, short-term counter-trend): in JST 6-9, after a 1-hour move (4 M15 bars) >= k x ATR(H1), sell a rise /
   buy a fall at the next M15 open. Stop beyond the impulse extreme + 0.2 ATR(H1). Target: 50% of the impulse back.
   Time exit after 8 M15 bars (2h). One trade at a time per pair. Cost 1.2 pip.
Reports first half / second half for each pair."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import turn_ea as TE  # noqa: E402
X = TE.X; B = TE.B
m15 = B.m15; T15 = pd.DatetimeIndex(B.T15); O, H, L, C = (m15[z].to_numpy(float) for z in 'ohlc'); N = len(C)
CL15 = X.CL15; C1 = np.array(B.C1, dtype='datetime64[ns]'); K1 = np.clip(np.searchsorted(C1, CL15.to_numpy(), side='right') - 1, 0, len(C1) - 1); a1 = B.A1[K1]
def to_jst(ts):
    t = pd.DatetimeIndex(ts).tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').tz_convert('Asia/Tokyo')
    return np.where(pd.isna(t), -1, t.hour).astype(int)
JST = to_jst(T15)
OUT = B.HERE / 'results' / 'session'; OUT.mkdir(parents=True, exist_ok=True)
def stats(lab, t, R):
    t = pd.DatetimeIndex(t); R = np.asarray(R); m = t.year >= 2005; t = t[m]; R = R[m]
    def pf(r): w = r > 0; return r[w].sum() / max(1e-9, -r[~w].sum())
    a = R[t.year <= 2015]; b = R[t.year >= 2016]
    print(f'{lab:30s} n={len(R):4d} {R.sum():+6.1f}R PF{pf(R):.2f} 勝率{(R > 0).mean():.0%} | 前半 {len(a)}回 {a.sum():+.1f}R PF{pf(a):.2f} | 後半 {len(b)}回 {b.sum():+.1f}R PF{pf(b):.2f}', flush=True)
# ---- EV
base = TE.events('M15', 'same')
def hrs(ev, ok):
    j = to_jst([e['t'] - pd.Timedelta(minutes=15) for e in ev])
    return [e for e, h in zip(ev, j) if ok(h)]
for lab, ok in (('EV 18-21', lambda h: 18 <= h < 21), ('EV 18-24', lambda h: h >= 18), ('EV 18-21+0-3', lambda h: 18 <= h < 21 or 0 <= h < 3), ('J 全時間（比較）', lambda h: h >= 0)):
    tr = X.run(hrs(base, ok), dict(trig='now', stop='ref', buf=0.3, exit='h1', act=1.0, win=1))
    tr.to_csv(OUT / f"ev_{lab.split()[1] if lab.startswith('EV') else 'all'}.csv", index=False); stats(lab, tr.t, tr.R)
# ---- TF
for k in (1.0, 1.5):
    for hold in (8, 16):
        res = []; i = 4; busy = -1
        while i < N - hold - 1:
            if JST[i] < 6 or JST[i] >= 9 or i <= busy or not a1[i] > 0:
                i += 1; continue
            mv = (C[i] - C[i - 4]) / a1[i]
            if abs(mv) < k:
                i += 1; continue
            s = -1 if mv > 0 else 1                      # fade
            e = O[i + 1]; ext = H[i - 3:i + 1].max() if s == -1 else L[i - 3:i + 1].min()
            sl = ext - s * 0.2 * a1[i]; risk = s * (e - sl)
            if risk <= 2e-4:
                i += 1; continue
            tp = e + s * 0.5 * abs(C[i] - C[i - 4])
            R = None
            for j in range(i + 1, i + 1 + hold):
                if (L[j] <= sl) if s == 1 else (H[j] >= sl): R = -1.0; break
                if (H[j] >= tp) if s == 1 else (L[j] <= tp): R = s * (tp - e) / risk; break
            if R is None: R = s * (C[i + hold] - e) / risk; j = i + hold
            res.append((T15[i + 1], R - 1.2e-4 / risk)); busy = j; i = j + 1
        d = pd.DataFrame(res, columns=['t', 'R']); d.to_csv(OUT / f'tf_k{k}_h{hold}.csv', index=False)
        stats(f'TF k{k} 保有{hold * 15}分', d.t, d.R)
