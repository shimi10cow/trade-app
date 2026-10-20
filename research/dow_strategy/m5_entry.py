"""M5 entry timing for the 5 EAs (2026-10-20).
Keep each EA's signal; after its entry bar, wait up to `win` M5 bars for an M5 turn in the trade direction
(prov: provisional turn / major: major reversal / brk: close beyond the last confirmed M5 swing against us = break of the
pullback's last lower high for a buy). Enter at that M5 close, stop beyond the last confirmed M5 swing (+buf x ATR(M5)),
never wider than the original stop. Exit: the original trade's exit (time/price) unless the new stop is hit first.
No trigger within `win` -> trade skipped. R is in units of the new (smaller) risk, cost 1.2 pips."""
import sys, os
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import m5_base as MB  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
D = Path(__file__).parent / 'results'
COST = 1.2e-4
FILES = [('R', 'regime2_R2c.csv'), ('T', 'regime2_T1t.csv'), ('L', 'tl_N2.csv'), ('A', 'retest_N1.csv'), ('C', 'step2/cl15_md4tri.csv')]
BL = ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))
m5, R5 = MB.get()
T5 = pd.DatetimeIndex(m5.t); H, L, C = (m5[z].to_numpy(float) for z in 'hlc'); A5 = atr(m5); N = len(T5)
EV = {}
for e in R5['prov_events']:
    if e['action'] in ('REVERSAL', 'PROV_START'):
        EV.setdefault(('prov', e['to']), []).append(e['idx'])
for e in R5['events']:
    if e.get('machine') == 'major' and e['action'] == 'REVERSAL':
        EV.setdefault(('major', e['to']), []).append(e['idx'])
EV = {k: np.array(sorted(v)) for k, v in EV.items()}
PV = sorted((e['available_idx'], e['kind'], e['price']) for e in R5['pivot_events'] if e.get('action', 'confirm') == 'confirm')
PA = np.array([p[0] for p in PV]); PK = np.array([p[1] for p in PV]); PP = np.array([p[2] for p in PV])


def load(name, f):
    d = pd.read_csv(D / f)
    if 'Rc' in d:
        t0 = pd.to_datetime(d.time) + pd.Timedelta(minutes=15); xt = pd.to_datetime(d.ExitTime); R = d.Rc
    else:
        t0 = pd.to_datetime(d.t); xt = pd.to_datetime(d.exit_t); R = d.R
    out = pd.DataFrame(dict(src=name, t0=t0, xt=xt, side=d.side, entry=d.entry, risk=d.risk, xp=d.exit, R=R))
    return out[out.t0.dt.year >= 2005].reset_index(drop=True)


def last_swing(i, kind):
    k = np.searchsorted(PA, i, side='right') - 1
    while k >= 0 and PK[k] != kind:
        k -= 1
    return PP[k] if k >= 0 else None


def one(x, trig, win, buf):
    s = x.side; j0 = T5.searchsorted(x.t0); je = min(T5.searchsorted(x.xt + pd.Timedelta(minutes=15)), N - 1)
    if j0 >= je:
        return None
    if trig == 'now':
        cand = [j0]
    elif trig == 'brk':
        cand = []
        for j in range(j0, min(j0 + win, je)):
            sw = last_swing(j, 'hi' if s == 1 else 'lo')
            if sw is not None and s * (C[j] - sw) > 0:
                cand = [j]; break
    else:
        arr = EV.get((trig, 'up' if s == 1 else 'down'), np.array([], int))
        k = np.searchsorted(arr, j0); cand = [arr[k]] if k < len(arr) and arr[k] < min(j0 + win, je) else []
    if not cand:
        return None
    j = cand[0]; e = C[j] if trig != 'now' else x.entry
    sw = last_swing(j, 'lo' if s == 1 else 'hi')
    st = (sw - s * buf * A5[j]) if sw is not None else None
    orig_st = x.entry - s * x.risk
    if st is None or s * (st - orig_st) < 0:      # never wider than the original stop
        st = orig_st
    risk = s * (e - st)
    if risk <= 2e-4:                               # at least 2 pips
        return None
    seg = L[j + 1:je + 1] if s == 1 else H[j + 1:je + 1]
    hit = np.nonzero(seg <= st)[0] if s == 1 else np.nonzero(seg >= st)[0]
    if len(hit):
        return -1 - COST / risk, risk
    return s * (x.xp - e) / risk - COST / risk, risk


if __name__ == '__main__':
    TR = pd.concat([load(*f) for f in FILES]).reset_index(drop=True)
    TR = TR[(TR.t0 >= T5[0]) & (TR.xt <= T5[-1])].reset_index(drop=True)
    y = TR.t0.dt.year.to_numpy()
    def rep(lab, r, risk):
        ok = ~np.isnan(r); rr = r[ok]; w = rr > 0
        b = [np.nansum(r[(y >= a) & (y <= z)]) for a, z in BL]
        parts = ' '.join(f'{c}:{np.nansum(r[(TR.src == c).to_numpy()]):+.0f}' for c in 'RTLAC')
        print(f'{lab:28s} {ok.sum():4d}回 {rr.sum():+7.1f}R PF{rr[w].sum() / -rr[~w].sum():.2f} 勝率{w.mean():.0%} 損切り中央{np.nanmedian(risk) / 1e-4:4.1f}p | '
              + ' '.join(f'{v:+.0f}' for v in b) + ' | ' + parts, flush=True)
    rep('元のまま', TR.R.to_numpy(), TR.risk.to_numpy())
    for trig in ('prov', 'major', 'brk'):
        for win in (12, 24, 48):
            for buf in (0.5, 1.0):
                res = [one(x, trig, win, buf) for x in TR.itertuples()]
                r = np.array([np.nan if v is None else v[0] for v in res]); rk = np.array([np.nan if v is None else v[1] for v in res])
                rep(f'M5 {trig} {win * 5}分以内 buf{buf}', r, rk)
