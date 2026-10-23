"""Index dip-buy (2026-10-23, own logic for US30 / US500 / JP225: upward drift + short-term mean reversion).
Long only. Context (uptrend): 'h4dow' = H4 major Dow trend up, or 'd1ma' = D1 close above a rising D1 SMA50.
Dip (setup, at an H1 close):
   'dep1.5' / 'dep2.5' : price fell >= k x ATR(H4) below the highest high of the last 30 H4 bars
   'ma75'              : H1 low touched the H4 SMA75 from above (close still above SMA75 - 1 ATR(H1))
Trigger within 24h: 'dow' = M15 provisional turn up, 'now' = next M15 open.
Stop: lowest low since the dip started (ref) - 0.3 ATR(H1). Exit: H1 / H4 swing trail from +1R, or a 2R target.
One setup per 24h. Writes results/idip/D_<ctx>_<dip>_<trig>_<exit>.csv"""
import sys, os, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'idip'; OUT.mkdir(parents=True, exist_ok=True)
X.add_trigger('now', lambda: {d: list(range(X.N)) for d in ('up', 'down')})
h4 = B.h4.reset_index(drop=True); C4 = pd.DatetimeIndex(B.C4); A4 = atr(h4)
H4h = h4.h.to_numpy(float); H4c = h4.c.to_numpy(float); ma75_4 = pd.Series(H4c).rolling(75).mean().to_numpy()
hh30 = pd.Series(H4h).rolling(30).max().to_numpy()
TR4 = [b[0] for b in B.R4['bars']]
h1 = B.h1.reset_index(drop=True); C1 = pd.DatetimeIndex(B.C1); A1 = np.asarray(B.A1, float)
H1l, H1c = h1.l.to_numpy(float), h1.c.to_numpy(float)
d1 = h4.assign(t=pd.to_datetime(h4.t)).set_index('t').c.resample('1D').last().dropna()
d1ma = d1.rolling(50).mean(); d1ok = ((d1 > d1ma) & (d1ma > d1ma.shift(5))); d1ok.index = d1ok.index + pd.Timedelta('1D')


def events(ctx, dip):
    ev = []; last = pd.Timestamp('1900-01-01'); low_since = None
    for j in range(200, len(h1)):
        t = C1[j]
        k4 = C4.searchsorted(t, 'right') - 1
        if k4 < 80: continue
        if ctx == 'h4dow': ok = TR4[k4] == 'up'
        else:
            i = d1ok.index.searchsorted(t, 'right') - 1; ok = bool(d1ok.iloc[i]) if i >= 0 else False
        if not ok or t - last < pd.Timedelta('24h'): continue
        if dip.startswith('dep'):
            k = float(dip[3:]); hit = hh30[k4] - H1c[j] >= k * A4[k4]
        else:
            m = ma75_4[k4]; hit = np.isfinite(m) and H1l[j] <= m and H1c[j] >= m - A1[j]
        if not hit: continue
        j0 = max(0, j - 30); ref = H1l[j0:j + 1].min()
        ev.append(dict(t=t, side=1, ref=ref, tag=f'{ctx}_{dip}', win=24)); last = t
    return ev


def run1(c):
    ctx, dip, trig, ex = c
    ev = events(ctx, dip)
    cfg = dict(trig=trig, stop='ref', buf=0.3, win=24, one_per_side=True)
    cfg.update(dict(exit='h1', act=1.0) if ex == 'h1' else dict(exit='h4', act=1.0) if ex == 'h4' else dict(exit='h1', act=99, tp=2.0))
    tr = X.run(ev, cfg); name = f'D_{ctx}_{dip}_{trig}_{ex}'
    if len(tr): tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, len(ev), len(tr), round(tr.R.sum(), 1) if len(tr) else 0


if __name__ == '__main__':
    G = list(itertools.product(('h4dow', 'd1ma'), ('dep1.5', 'dep2.5', 'ma75'), ('dow', 'now'), ('h1', 'h4', 'tp2')))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for r in p.imap_unordered(run1, G): print(*r, flush=True)
