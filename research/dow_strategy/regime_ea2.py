"""Step 1 (2026-10-20): EA-R / EA-T with the rules learned from the user's labels, and alternative stops.
  filters : maxdev (|distance from H4 SMA75| <= 3 ATR, 'not stretched'), notri (no entry while an H4 triangle forms)
  stops   : default (beyond M15 SMA200) | M15 swing | H1 swing | H1 SMA75 | H1 SMA200, each + 0.5 x ATR(H1)
Usage: EA_M15_CACHE=<csv> python dow_strategy/regime_ea2.py [keys]"""
import bisect, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import regime_ea as RE  # noqa: E402  (gate_R, gate_T, LV = long_validation)
import env_ctx as EC  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
LV = RE.LV
h1 = LV.h1.reset_index(drop=True); C1 = LV.h1_close; A1 = atr(h1)
_R1 = dow_trend.run(h1, 'H1')
H1P = sorted(((C1[e['available_idx']], e['kind'], e['price']) for e in _R1['pivot_events']), key=lambda x: x[0]); H1PT = [x[0] for x in H1P]
M15P = LV.trail.sort_values('confirm_time').reset_index(drop=True); M15PT = list(M15P.confirm_time)
MA = {n: h1.c.rolling(n).mean().to_numpy() for n in (75, 200)}


def _last(P, PT, t, kind, getk, getp):
    j = bisect.bisect_right(PT, t) - 1
    while j >= 0 and getk(P, j) != kind:
        j -= 1
    return getp(P, j) if j >= 0 else None


def stop_fn(kind, buf=0.5):
    def f(t, s, entry, sl):
        tc = t + pd.Timedelta(minutes=15)
        k = bisect.bisect_right(C1, tc) - 1
        if k < 0:
            return None
        if kind == 'h1sw':
            ref = _last(H1P, H1PT, tc, 'lo' if s == 1 else 'hi', lambda P, j: P[j][1], lambda P, j: P[j][2])
        elif kind == 'm15sw':
            ref = _last(M15P, M15PT, tc, 'L' if s == 1 else 'H', lambda P, j: P.kind[j], lambda P, j: P.price[j])
        else:
            ref = MA[int(kind[4:])][k]
        if ref is None or not np.isfinite(ref):
            return None
        p = ref - s * buf * A1[k]
        return p if s * (entry - p) > 0 else None
    return f


def both(*fs):
    return lambda t, s: all(f(t, s) for f in fs)


def env(**kw):
    return lambda t, s: EC.env_ok(kw, t + pd.Timedelta(minutes=15), s)


R0 = RE.gate_R(0.08, 3); T0 = RE.gate_T(0, 0.10)
SPECS = {
    'R1m': ('EA-R＋伸びすぎ除外(SMA75 3ATR)', lambda: LV.E.Config(extra_filter=both(R0, env(maxdev=3)))),
    'R1t': ('EA-R＋H4三角の最中は除外', lambda: LV.E.Config(extra_filter=both(R0, env(notri='H4')))),
    'R1mt': ('EA-R＋両方', lambda: LV.E.Config(extra_filter=both(R0, env(maxdev=3, notri='H4')))),
    'T1m': ('EA-T＋伸びすぎ除外', lambda: LV.E.Config(use_long_ma=False, extra_filter=both(T0, env(maxdev=3)))),
    'T1t': ('EA-T＋H4三角の最中は除外', lambda: LV.E.Config(use_long_ma=False, extra_filter=both(T0, env(notri='H4')))),
    'T1mt': ('EA-T＋両方', lambda: LV.E.Config(use_long_ma=False, extra_filter=both(T0, env(maxdev=3, notri='H4')))),
    'T1m4': ('EA-T＋伸びすぎ除外(4ATR)', lambda: LV.E.Config(use_long_ma=False, extra_filter=both(T0, env(maxdev=4)))),
    'R1m4': ('EA-R＋伸びすぎ除外(4ATR)', lambda: LV.E.Config(extra_filter=both(R0, env(maxdev=4)))),
}
SPECS.update({
    'R2a': ('EA-R 新レンジ判定(スコア>0.6)', lambda: LV.E.Config(extra_filter=env(env='R2', rs_hi=0.6))),
    'R2b': ('EA-R 新レンジ判定(スコア>0.5)', lambda: LV.E.Config(extra_filter=env(env='R2', rs_hi=0.5))),
    'R2c': ('EA-R 新レンジ判定(スコア>0.7)', lambda: LV.E.Config(extra_filter=env(env='R2', rs_hi=0.7))),
    'R2d': ('EA-R 新レンジ判定(スコア>0.6)＋H4三角の最中は除外', lambda: LV.E.Config(extra_filter=env(env='R2', rs_hi=0.6, notri='H4'))),
    'T2a': ('EA-T 新判定(スコア<0.4)', lambda: LV.E.Config(use_long_ma=False, extra_filter=env(env='T2', rs_lo=0.4))),
    'T2b': ('EA-T 新判定(スコア<0.5)', lambda: LV.E.Config(use_long_ma=False, extra_filter=env(env='T2', rs_lo=0.5))),
    'T2c': ('EA-T 新判定(スコア<0.3)', lambda: LV.E.Config(use_long_ma=False, extra_filter=env(env='T2', rs_lo=0.3))),
})
for st in ('m15sw', 'h1sw', 'h1ma75', 'h1ma200'):
    SPECS[f'Rs_{st}'] = (f'EA-R 損切り={st}', (lambda st=st: LV.E.Config(extra_filter=R0, sl_fn=stop_fn(st))))
    SPECS[f'Ts_{st}'] = (f'EA-T 損切り={st}', (lambda st=st: LV.E.Config(use_long_ma=False, extra_filter=T0, sl_fn=stop_fn(st))))


def run2(key):
    name, mk = SPECS[key]; t0 = time.time()
    tr = LV.E.run_pair('EURUSD', mk()); tr['Rc'] = tr.R - LV.COST / tr.risk
    tr.to_csv(LV.OUT / f'regime2_{key}.csv', index=False)
    return key, name, tr, time.time() - t0


if __name__ == '__main__':
    keys = sys.argv[1:] or list(SPECS)
    with Pool(4) as pool:
        for key, name, tr, sec in pool.imap_unordered(run2, keys):
            y = pd.to_datetime(tr.time).dt.year; tr = tr[y >= 2005]; y = y[y >= 2005]; r = tr.Rc
            b = [r[(y >= a) & (y <= z)].sum() for a, z in ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]
            yy = tr.groupby(y).Rc.sum(); st = LV.stats(r.to_numpy())
            print(f"[{key}] {name}: {st['n']}回 {st['sumR']:+.1f}R PF{st['PF']:.2f} DD{st['maxDD']:.1f} 負け年{(yy < 0).sum()}/{len(yy)} 損切り中央{tr.risk.median() / 1e-4:.0f}p | "
                  + ' '.join(f'{v:+.1f}' for v in b) + ('  ★' if min(b) > 0 else ''), flush=True)
