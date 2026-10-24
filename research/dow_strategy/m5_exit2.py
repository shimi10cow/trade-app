"""M5 early warning for the exit the M15/H1 logic would take anyway (user 2026-10-21).
For every trade we rebuild a causal stop path (initial stop; from +1R the H1 swing trail, only tightening) on M5 bars and
look for an M5 alarm while the trade is in a danger zone:
  alarm  big1.5 / big2 / big3 : an M5 candle whose body against the position is >= k x ATR(M5)
         m5maj                : the M5 major trend reverses against the position
  zone   none   : anywhere
         stop   : price within 0.5 x ATR(H1) of the current stop (the M15/H1 exit is close)
         m15    : the M15 provisional trend (last closed M15 bar) is against the position
         stop|m15
  phase  all / early (before the trade reached +1R) / late (after +1R)
Exit at the M5 close of the alarm bar (cost 1.2 pip). Compared with the original trade result.
'good save' = the original trade then exited within 24h at a worse price than the M5 exit.
Env: TRADE_FILES='R=regime2_R2c.csv,T=...' (relative to results/), M5_SYM."""
import os, sys, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m5_base as MB  # noqa: E402
import dow_turn_ea as B  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
RES = Path(__file__).resolve().parent / 'results'
FILES = [x.split('=') for x in os.environ.get('TRADE_FILES', 'R=regime2_R2c.csv,T=regime2_T1t.csv,L=tl_N2.csv,A=retest_N1.csv,C=step2/cl15_md4tri.csv').split(',')]
COST = 1.2e-4; PIP = 1e-4
if os.environ.get('NO_M5DOW'):
    from env_recognition.data import load_m5
    m5 = load_m5(os.environ.get('M5_SYM', 'EURUSD')); m5 = m5[m5.t >= B.START - pd.Timedelta(days=5)].reset_index(drop=True); R5 = {'events': []}
else:
    m5, R5 = MB.get()
T5 = pd.DatetimeIndex(m5.t); O5, H5, L5, C5 = (m5[z].to_numpy(float) for z in 'ohlc'); A5 = atr(m5); N = len(T5)
CL5 = T5 + pd.Timedelta(minutes=5)
# H1 swings known at each M5 close, H1 ATR, M15 provisional trend of the last closed M15 bar
H1P = B.H1P; HT = np.array([p[0] for p in H1P], dtype='datetime64[ns]')
k = np.searchsorted(HT, CL5.to_numpy(), side='right') - 1
lastlo = np.full(N, np.nan); lasthi = np.full(N, np.nan); lo_v = np.nan; hi_v = np.nan; ptr = -1
for j in range(N):
    while ptr + 1 <= k[j]:
        ptr += 1
        if H1P[ptr][1] == 'lo': lo_v = H1P[ptr][2]
        else: hi_v = H1P[ptr][2]
    lastlo[j] = lo_v; lasthi[j] = hi_v
C1 = np.array(B.C1, dtype='datetime64[ns]'); k1 = np.clip(np.searchsorted(C1, CL5.to_numpy(), side='right') - 1, 0, len(C1) - 1); AH1 = B.A1[k1]
CL15 = (B.T15 + pd.Timedelta(minutes=15)).to_numpy(); k15 = np.searchsorted(CL15, CL5.to_numpy(), side='right') - 1
P15 = np.array([b[0] for b in B.R15['prov_bars']], dtype=object); m15dir = np.where(k15 >= 0, P15[np.clip(k15, 0, len(P15) - 1)], None)
MAJ = {'up': np.zeros(N, bool), 'down': np.zeros(N, bool)}
for e in R5['events']:
    if e.get('machine') == 'major' and e['action'] == 'REVERSAL': MAJ[e['to']][e['idx']] = True
BODY = (C5 - O5) / A5
def load(name, f):
    d = pd.read_csv(RES / f)
    if 'Rc' in d: t0 = pd.to_datetime(d.time) + pd.Timedelta(minutes=15); xt = pd.to_datetime(d.ExitTime); R = d.Rc
    else: t0 = pd.to_datetime(d.t); xt = pd.to_datetime(d.exit_t); R = d.R
    o = pd.DataFrame(dict(src=name, t0=t0, xt=xt, side=d.side, entry=d.entry, risk=d.risk, xp=d.exit, R=R))
    return o[(o.t0.dt.year >= 2005) & (o.t0 >= T5[0]) & (o.xt <= T5[-1])].reset_index(drop=True)
TR = pd.concat([load(n, f) for n, f in FILES]).reset_index(drop=True)
# per-trade slices (precomputed once)
SL = []
for x in TR.itertuples():
    j0 = T5.searchsorted(x.t0); je = T5.searchsorted(x.xt)
    if je <= j0 + 1: SL.append(None); continue
    s = x.side; ix = np.arange(j0, je)
    fav = (H5[ix] - x.entry) / x.risk if s == 1 else (x.entry - L5[ix]) / x.risk
    mfe = np.maximum.accumulate(fav)
    sl0 = x.entry - s * x.risk
    cand = (lastlo[ix] - PIP) if s == 1 else (lasthi[ix] + PIP)
    ok = (mfe >= 1) & np.isfinite(cand) & ((cand < C5[ix]) if s == 1 else (cand > C5[ix]))
    raw = np.where(ok, cand, sl0 if s == 1 else sl0)
    stop = np.maximum.accumulate(np.maximum(raw, sl0)) if s == 1 else np.minimum.accumulate(np.minimum(raw, sl0))
    dist = s * (C5[ix] - stop) / AH1[ix]
    against = 'down' if s == 1 else 'up'
    m15a = m15dir[ix] == against
    big = -s * BODY[ix]
    SL.append(dict(ix=ix, mfe=mfe, dist=dist, m15a=m15a, big=big, maj=MAJ[against][ix]))
def apply(trig, zone, phase, zd=0.5):
    r = TR.R.to_numpy().copy(); fired = 0; good = 0; lost = 0.0
    for q, (x, z) in enumerate(zip(TR.itertuples(), SL)):
        if z is None: continue
        a = (z['maj'] if trig == 'm5maj' else z['big'] >= float(trig[3:]))
        near = z['dist'] <= zd
        if zone == 'stop': a = a & near
        elif zone == 'm15': a = a & z['m15a']
        elif zone == 'stop|m15': a = a & (near | z['m15a'])
        elif zone == 'stop&m15': a = a & near & z['m15a']
        if phase == 'early': a = a & (z['mfe'] < 1)
        elif phase == 'late': a = a & (z['mfe'] >= 1)
        h = np.nonzero(a)[0]
        if not len(h): continue
        j = z['ix'][h[0]]; nr = x.side * (C5[j] - x.entry) / x.risk - COST / x.risk
        fired += 1
        if (x.xt - T5[j]) <= pd.Timedelta(hours=24) and nr > x.R: good += 1
        r[q] = nr
    return r, fired, good
if __name__ == '__main__':
    y = TR.t0.dt.year.to_numpy(); base = TR.R.sum()
    print(f'基準 {len(TR)}回 {base:+.1f}R  ' + ' '.join(f"{c}:{TR.R[TR.src == c].sum():+.0f}" for c in TR.src.unique()))
    rows = []
    GRID = list(itertools.product(('big1.5', 'big2', 'big3', 'm5maj'), ('none', 'stop', 'm15', 'stop|m15'), ('all', 'early', 'late'), (0.5,)))
    if os.environ.get('GRID3'):
        GRID = list(itertools.product(('big1.5', 'big2', 'big2.5', 'big3'), ('stop', 'none'), ('all', 'early', 'late'), (1.0, 1.5, 2.0, 2.5, 3.0)))
    if os.environ.get('GRID2'):
        GRID = list(itertools.product(('big2', 'big3', 'm5maj'), ('stop', 'stop&m15'), ('all', 'early', 'late'), (0.25, 0.5, 1.0, 1.5, 2.0)))
    for trig, zone, phase, zd in GRID:
        r, f, g = apply(trig, zone, phase, zd)
        b = [r[(y >= a) & (y <= c)].sum() - TR.R[(y >= a) & (y <= c)].sum() for a, c in ((2005, 2015), (2016, 2026))]
        rows.append(dict(trig=trig, zone=zone, phase=phase, zd=zd, fired=f, good_save=g, total=r.sum(), diff=r.sum() - base, first=b[0], second=b[1],
                         **{f'd_{c}': r[(TR.src == c).to_numpy()].sum() - TR.R[TR.src == c].sum() for c in TR.src.unique()}))
    D = pd.DataFrame(rows).sort_values('diff', ascending=False)
    D.to_csv(RES / f"m5_exit2_{os.environ.get('M5_SYM', 'EURUSD')}{'_g2' if os.environ.get('GRID2') else ''}{'_g3' if os.environ.get('GRID3') else ''}.csv", index=False)
    pd.set_option('display.width', 250); print(D.round(1).head(20).to_string(index=False)); print('...'); print(D.round(1).tail(5).to_string(index=False))
