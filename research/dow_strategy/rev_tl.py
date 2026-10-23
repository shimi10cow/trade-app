"""Counter-trend at a strong horizontal level, entered on the M15 trend line break (user, 2026-10-23).
Level  : a confirmed H4 swing high (low) that became a real peak: price fell >= 3 ATR(H4) from it before trading above it
         (known from that moment). It dies when an H4 bar closes beyond it by 0.25 ATR(H4).
         reactions = later H4 visits within 0.25 ATR(H4) that closed back below it, each after price had been >= 1.5 ATR away.
Approach : an H1 bar comes up to within 0.3 ATR(H4) of the level from below (previous close further away), H1 close not
         beyond +0.25 ATR(H4). Features (filtered later, tag = react|run|h1dow|drop):
           run   = rise into the level over the last 48 H1 bars (ATR H1)   (trend running into the level, not a range)
           h1dow = H1 Dow (last two H1 swings) with the move into the level (+1) / against (-1) / mixed (0)
Trigger within 24h after the approach (cancelled once an M15 close goes beyond the level by 0.5 ATR(H4)), sell side:
   tl     : the M15 rising impulse line breaks (mtf_break.py events)
   dow    : M15 provisional turn down
   tl_dow : M15 line break, then the M15 turn down within 8h
   tl_ma  : M15 line break with the M15 close below SMA20(M15)
   h1p    : the H1 provisional trend turns with the trade (48h), then an M15 pullback (turn against) and the M15 turn back
Tag also carries RSI(14): H1 at the approach (max for a sell over the last 6 H1 bars) and M15 before the trigger (16 bars).
Stop: above the highest high since the approach + buf x ATR(H1).
Exit: tp2 (2R) / h1 (H1 swing trail from +1R) / m15 (M15 swing trail from +1R) / sw (target = last confirmed H1 swing low; 3R if that is already passed
for a sell, i.e. the push low of the trend that ran into the level) / ma (target = H1 SMA75)
Run in a workspace (after mtf_break.py). Writes results/rev/RV_<trig>_<buf>_<exit>.csv"""
import os, sys, bisect, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ea_core as X  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
B = X.B
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SYM = os.environ.get('M5_SYM', 'EURUSD')
OUT = B.HERE / 'results' / 'rev'; OUT.mkdir(parents=True, exist_ok=True)
h4 = B.h4.reset_index(drop=True); C4 = pd.DatetimeIndex(B.C4); A4 = np.asarray(atr(h4), float)
H4h, H4l, H4c = (h4[z].to_numpy(float) for z in 'hlc')
h1 = B.h1.reset_index(drop=True); C1 = pd.DatetimeIndex(B.C1); A1 = np.asarray(B.A1, float)
H1h, H1l, H1c = (h1[z].to_numpy(float) for z in 'hlc')
CL15 = X.CL15; Mh, Ml, Mc = B.h, B.l, B.c
MA20 = pd.Series(Mc).rolling(20).mean().to_numpy()


def rsi(c, n=14):
    d = pd.Series(c).diff(); up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return (100 - 100 / (1 + up / dn)).to_numpy()


RSI15 = rsi(Mc); RSI1 = rsi(H1c); H1MA75 = pd.Series(H1c).rolling(75).mean().to_numpy()
H1TURN = {d: sorted(e['idx'] for e in B.R1['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d) for d in ('up', 'down')}
H1P = B.H1P; H1PT = pd.DatetimeIndex(B.H1PT)


def h1dow(t):
    k = H1PT.searchsorted(t, 'right'); hs = [p for _, kd, p in H1P[max(0, k - 12):k] if kd == 'hi'][-2:]; ls = [p for _, kd, p in H1P[max(0, k - 12):k] if kd == 'lo'][-2:]
    if len(hs) < 2 or len(ls) < 2: return 0
    return 1 if (hs[1] > hs[0] and ls[1] > ls[0]) else (-1 if (hs[1] < hs[0] and ls[1] < ls[0]) else 0)


# ---- levels from H4 swings
levels = []
for e in B.R4['pivot_events']:
    s = -1 if e['kind'] == 'hi' else 1                 # the trade side at this level: sell at a high, buy at a low
    ix, pl = e['idx'], e['price']; av = e['available_idx']
    a = A4[ix] if np.isfinite(A4[ix]) else np.nan
    if not np.isfinite(a): continue
    tv = None; tb = None; react = []; away = False
    for k in range(ix + 1, len(h4)):
        beyond = (H4c[k] > pl + 0.25 * a) if s == -1 else (H4c[k] < pl - 0.25 * a)
        if beyond: tb = C4[k]; break
        dist = (pl - H4l[k]) / a if s == -1 else (H4h[k] - pl) / a
        if tv is None:
            if dist >= 3: tv = C4[max(k, av)]; away = True
            continue
        near = ((H4h[k] >= pl - 0.25 * a) if s == -1 else (H4l[k] <= pl + 0.25 * a))
        if dist >= 1.5: away = True
        elif near and away: react.append(C4[k]); away = False
    if tv is not None:
        levels.append(dict(side=s, p=pl, a=a, tv=tv, tb=tb or pd.Timestamp('2100-01-01'), react=react, drop=None))
print(SYM, len(levels), 'levels', flush=True)

# ---- approaches (H1)
appr = []
for L in levels:                                       # vectorised per level: H1 bars inside its life that come up to it
    s, pl, a = L['side'], L['p'], L['a']
    j0 = max(49, C1.searchsorted(L['tv'], 'right')); j1 = C1.searchsorted(L['tb'], 'left')
    if j1 <= j0: continue
    jj = np.arange(j0, j1)
    if s == -1: ok = (H1h[jj] >= pl - 0.3 * a) & (H1c[jj - 1] < pl - 0.3 * a) & (H1c[jj] <= pl + 0.25 * a)
    else: ok = (H1l[jj] <= pl + 0.3 * a) & (H1c[jj - 1] > pl + 0.3 * a) & (H1c[jj] >= pl - 0.25 * a)
    lastt = pd.Timestamp('1900-01-01')
    for j in jj[ok]:
        t = C1[j]
        if t - lastt < pd.Timedelta('48h'): continue
        lastt = t
        a1 = A1[j] if np.isfinite(A1[j]) and A1[j] > 0 else np.nan
        run = ((H1c[j] - H1l[j - 48:j + 1].min()) if s == -1 else (H1h[j - 48:j + 1].max() - H1c[j])) / a1
        appr.append(dict(t=t, side=s, p=pl, a=a, react=sum(1 for r in L['react'] if r < t), run=run, h1d=h1dow(t) * (-s)))
AP = pd.DataFrame(appr).sort_values('t').reset_index(drop=True)
print(len(AP), 'approaches', flush=True)

# ---- triggers (M15)
BR = pd.read_pickle(f'{S}/feat/m15brk_{SYM}.pkl')
TURN = {d: sorted(e['idx'] for e in B.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d) for d in ('up', 'down')}
EV = {k: [] for k in ('tl', 'dow', 'tl_dow', 'tl_ma', 'h1p')}
for x in AP.itertuples():
    s = x.side; i0 = CL15.searchsorted(x.t); i1 = CL15.searchsorted(x.t + pd.Timedelta('24h'))
    seg = Mc[i0:i1]; bad = np.nonzero((seg > x.p + 0.5 * x.a) if s == -1 else (seg < x.p - 0.5 * x.a))[0]
    if len(bad): i1 = i0 + bad[0]
    if i1 <= i0: continue
    j = C1.searchsorted(x.t)
    r1 = np.nanmax(RSI1[max(0, j - 6):j + 1]) if s == -1 else np.nanmin(RSI1[max(0, j - 6):j + 1])   # H1 RSI into the level
    tag0 = f'{x.react}|{x.run:.2f}|{x.h1d}|{r1:.1f}'
    bt = BR[(BR.side == -s) & (BR.t >= CL15[i0]) & (BR.t < CL15[min(i1, len(CL15) - 1)])].t
    ib = [int(CL15.searchsorted(t)) for t in bt]
    tl = ib[0] if ib else None
    lst = TURN['up' if s == 1 else 'down']; k = bisect.bisect_left(lst, i0); dw = lst[k] if k < len(lst) and lst[k] < i1 else None
    tld = None
    if tl is not None:
        k = bisect.bisect_left(lst, tl); tld = lst[k] if k < len(lst) and lst[k] < min(i1, tl + 32) else None
    tlm = next((i for i in ib if ((Mc[i] < MA20[i]) if s == -1 else (Mc[i] > MA20[i]))), None)
    # h1p: H1 turns with the trade (48h, level not broken) -> M15 pullback (turn against, 24h) -> M15 turn back
    hp = None; i2 = CL15.searchsorted(x.t + pd.Timedelta('48h'))
    l1 = H1TURN['up' if s == 1 else 'down']; k = bisect.bisect_left(l1, j)
    if k < len(l1) and C1[l1[k]] <= x.t + pd.Timedelta('48h'):
        ih = CL15.searchsorted(C1[l1[k]])
        segb = Mc[i0:ih + 1]
        if not ((segb > x.p + 0.5 * x.a) if s == -1 else (segb < x.p - 0.5 * x.a)).any():
            lo_ = TURN['down' if s == 1 else 'up']; k2 = bisect.bisect_left(lo_, ih)
            if k2 < len(lo_) and lo_[k2] < ih + 96:
                k3 = bisect.bisect_left(lst, lo_[k2]); hp = lst[k3] if k3 < len(lst) and lst[k3] < lo_[k2] + 96 else None
    for nm, i in (('tl', tl), ('dow', dw), ('tl_dow', tld), ('tl_ma', tlm), ('h1p', hp)):
        if i is None: continue
        ref = Mh[i0:i + 1].max() if s == -1 else Ml[i0:i + 1].min()
        r15 = np.nanmax(RSI15[max(0, i - 16):i + 1]) if s == -1 else np.nanmin(RSI15[max(0, i - 16):i + 1])
        kk = bisect.bisect_right(B.C1, CL15[i]) - 1
        sw = X._last_swing(B.H1P, B.H1PT, CL15[i], 'lo' if s == -1 else 'hi')     # H1 push low (for a sell) = target
        EV[nm].append(dict(t=CL15[i], side=s, ref=ref, win=0.3, tag=f'{tag0}|{r15:.1f}', tp_sw=sw, tp_ma=H1MA75[kk]))
print({k: len(v) for k, v in EV.items()}, flush=True)
X.add_trigger('all', lambda: {'up': list(range(X.N)), 'down': list(range(X.N))})


def run1(c):
    trig, buf, ex = c
    cfg = dict(trig='all', stop='ref', buf=buf, win=0.3, one_per_side=True)
    ev = EV[trig]
    if ex == 'h1': cfg.update(exit='h1', act=1.0)
    elif ex == 'm15': cfg.update(exit='m15', act=1.0)
    elif ex in ('sw', 'ma'): cfg.update(exit='h1', act=99, tp_px=True, tp=3.0); ev = [dict(e, tp_px=e['tp_sw' if ex == 'sw' else 'tp_ma']) for e in ev]
    else: cfg.update(exit='h1', act=99, tp=float(ex[2:]))
    tr = X.run(ev, cfg); name = f'RV_{trig}_{buf}_{ex}'
    if len(tr): tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, len(EV[trig]), len(tr), round(tr.R.sum(), 1) if len(tr) else 0


if __name__ == '__main__':
    G = list(itertools.product(('tl', 'dow', 'tl_dow', 'tl_ma', 'h1p'), (0.3,), ('tp2', 'h1', 'm15', 'sw', 'ma')))
    with Pool(int(os.environ.get('NPROC', '2'))) as p:
        for r in p.imap_unordered(run1, G): print(*r, flush=True)
