"""Counter-move entries at horizontal zones (user idea, 2026-10-23). Zones = env_recognition.zones (H4 or D1 Dow levels:
broken 押し安値/戻り高値, provisional ones, W necks), only known after activation, gone after expiry.
Touch: an H1 bar whose previous close was outside the zone reaches into it (from above -> buy bounce, from below -> sell)
without closing beyond the far edge. Entry two timeframes lower than the zone:
  p1 : after the touch, the H1 provisional trend turns in the bounce direction (within 48h, zone not broken), then the
       first M15 pullback (M15 turn against) and the M15 turn back -> entry   ('H1 turn, buy the M15 pullback')
  p2 : first M15 trigger in the bounce direction within 12h of the touch ('dow' = M15 provisional turn, 'stoch')
Stop: beyond the zone's far edge (+buf x ATR(H1)). Exit: fixed target tp R, or H1 swing trail from +1R.
Each trade carries tag = '<tf>_<with|against>' (bounce direction vs the H4 major trend at the touch).
Run inside a pair workspace (DT_START / DT_CACHE like the other EAs). Writes results/zone/Z_<...>.csv"""
import sys, os, bisect, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ea_core as X  # noqa: E402
from env_recognition import zones as ZN, dow_trend  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'zone'; OUT.mkdir(parents=True, exist_ok=True)

h1 = B.h1.reset_index(drop=True); C1 = pd.DatetimeIndex(B.C1)
H1o, H1h, H1l, H1c = (h1[z].to_numpy(float) for z in 'ohlc')
C4 = pd.DatetimeIndex(B.C4); R4BARS = B.R4['bars']; A1H = np.asarray(B.A1, float)


def zone_set(tf):
    if tf == 'H4':
        df, res, close = B.h4.reset_index(drop=True), B.R4, C4
    else:
        h4 = B.h4.copy(); h4['t'] = pd.to_datetime(h4.t)
        df = h4.set_index('t').resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
        res = dow_trend.run(df, 'D1'); close = pd.DatetimeIndex(df.t) + TF_LEN['D1']
    zs = ZN.build(df, res)
    return [dict(top=z['top'], bot=z['bottom'], t_on=close[z['activation']],
                 t_off=close[z['expiry']] if z['expiry'] is not None else pd.Timestamp('2100-01-01')) for z in zs]


def touches(tf):
    zs = zone_set(tf); ev = []; last = {}; cnt = {}
    for zi, z in enumerate(zs):
        j0 = C1.searchsorted(z['t_on'], 'left'); j1 = C1.searchsorted(z['t_off'], 'left')
        for j in range(max(j0, 1), min(j1, len(h1))):
            pc = H1c[j - 1]
            if pc > z['top'] and H1l[j] <= z['top'] and H1c[j] >= z['bot']: s, ref = 1, z['bot']
            elif pc < z['bot'] and H1h[j] >= z['bot'] and H1c[j] <= z['top']: s, ref = -1, z['top']
            else: continue
            if C1[j] - last.get((zi, s), pd.Timestamp('1900-01-01')) < pd.Timedelta('24h'): continue
            last[(zi, s)] = C1[j]; cnt[zi] = cnt.get(zi, 0) + 1
            a1 = A1H[j] if np.isfinite(A1H[j]) and A1H[j] > 0 else np.nan
            spd = 'fast' if j >= 12 and abs(H1c[j] - H1c[j - 12]) > 3 * a1 else 'slow'   # move into the zone over the last 12 H1 bars
            k4 = C4.searchsorted(C1[j], 'right') - 1
            tr = R4BARS[k4][0] if k4 >= 0 else None
            rel = 'with' if tr == ('up' if s == 1 else 'down') else 'against'
            ev.append(dict(t=C1[j], side=s, ref=ref, j=j, tag=f'{tf}_{rel}_t{min(cnt[zi], 3)}_{spd}', top=z['top'], bot=z['bot']))
    return sorted(ev, key=lambda e: e['t'])


# H1 provisional turns (known at the H1 close) and M15 provisional turns (known at the M15 close)
H1TURN = {d: sorted(C1[e['idx']] for e in B.R1['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d) for d in ('up', 'down')}
M15TURN = {d: sorted(X.CL15[e['idx']] for e in B.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d) for d in ('up', 'down')}


def first_after(lst, t, until):
    k = bisect.bisect_right(lst, t)
    return lst[k] if k < len(lst) and lst[k] <= until else None


def p1_events(tev):
    """touch -> H1 turn in bounce direction (48h, zone not broken) -> M15 turn against (pullback, 24h) -> setup known."""
    out = []
    for e in tev:
        d, o = ('up', 'down') if e['side'] == 1 else ('down', 'up')
        th = first_after(H1TURN[d], e['t'], e['t'] + pd.Timedelta('48h'))
        if th is None: continue
        j1 = C1.searchsorted(th, 'left')
        seg = H1c[e['j']:j1 + 1]
        if (e['side'] == 1 and (seg < e['ref']).any()) or (e['side'] == -1 and (seg > e['ref']).any()): continue
        tp = first_after(M15TURN[o], th, th + pd.Timedelta('24h'))
        if tp is None: continue
        out.append(dict(e, t=tp, win=24))
    return out


def run1(c):
    tf, pat, buf, ex = c
    tev = TEV[tf]
    if pat == 'p1': ev, trig, win = p1_events(tev), 'dow', 24
    else: ev, trig, win = [dict(e, win=12) for e in tev], ('dow' if pat == 'p2dow' else 'stoch'), 12
    cfg = dict(trig=trig, stop='ref', buf=buf, win=win, one_per_side=True)
    cfg.update(dict(exit='h1', act=1.0) if ex == 'h1' else dict(exit='h1', act=99, tp=float(ex[2:])))
    tr = X.run(ev, cfg)
    name = f'Z_{tf}_{pat}_{buf}_{ex}'
    if len(tr): tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, len(ev), len(tr), round(tr.R.sum(), 1) if len(tr) else 0


TEV = {tf: touches(tf) for tf in ('H4', 'D1')}
print({k: len(v) for k, v in TEV.items()}, 'touches', flush=True)
if __name__ == '__main__':
    G = list(itertools.product(('H4', 'D1'), ('p1', 'p2dow', 'p2st'), (0.3, 0.8), ('tp1.5', 'tp2', 'tp3', 'h1')))
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for r in p.imap_unordered(run1, G): print(*r, flush=True)
