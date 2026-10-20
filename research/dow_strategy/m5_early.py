"""Earlier entries with M5 (2026-10-20), for EAs whose setup is known before the trigger (ea_core):
trigger 'm5prov' / 'm5maj' = the M5 provisional / major turn in the setup direction (usually before the M15 turn);
entry at the next M15 open after that M5 bar closed (conservative). Stops: the setup's own ref, the last M15 swing,
or the last confirmed M5 swing (+buf x ATR(H1)). Everything else as the original EA (H1 trail from +1R, filters)."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
import m5_entry as ME  # noqa: E402
import step2_newea as S2  # noqa: E402
T5 = ME.T5
def m5trig(kind):
    def f():
        out = {}
        for d in ('up', 'down'):
            arr = ME.EV.get((kind, d), np.array([], int))
            i = X.CL15.searchsorted(T5[arr] + pd.Timedelta(minutes=5))
            out[d] = sorted(set(int(v) for v in i if v < X.N))
        return out
    return f
X.add_trigger('m5prov', m5trig('prov')); X.add_trigger('m5maj', m5trig('major'))
_orig = X.stop_ref
LOA = np.array([a for a, k in zip(ME.PA, ME.PK) if k == 'lo']); LOP = np.array([p for p, k in zip(ME.PP, ME.PK) if k == 'lo'])
HIA = np.array([a for a, k in zip(ME.PA, ME.PK) if k == 'hi']); HIP = np.array([p for p, k in zip(ME.PP, ME.PK) if k == 'hi'])
def stop_ref(kind, i, s, ev=None):
    if kind == 'm5swing':
        j = T5.searchsorted(X.CL15[i]) - 1                      # last M5 bar closed by the M15 close
        A_, P_ = (LOA, LOP) if s == 1 else (HIA, HIP)
        k = np.searchsorted(A_, j, side='right') - 1
        return P_[k] if k >= 0 else None
    return _orig(kind, i, s, ev)
X.stop_ref = stop_ref
BL = ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))


def rep(lab, tr):
    y = tr.t.dt.year; r = tr.R; w = r > 0
    b = [r[(y >= a) & (y <= z)].sum() for a, z in BL]; eq = r.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    print(f'{lab:34s} n={len(r):4d} {r.sum():+6.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} 勝率{w.mean():.0%} DD{dd:6.1f} SL{tr.risk.median() / 1e-4:4.0f}p | ' + ' '.join(f'{v:+.1f}' for v in b) + ('  ★' if min(b) > 0 else ''), flush=True)


if __name__ == '__main__':
    EV = S2.cl15_events()
    C0 = dict(trig='dow', stop='m15turn', buf=1.0, exit='h1', act=1.0, dside=0, maxdev=4, notri='H4')
    rep('C 元（M15仮転換）', X.run(EV, C0))
    for trig in ('m5prov', 'm5maj'):
        for stop, buf in (('m5swing', 0.2), ('m5swing', 0.5), ('m15swing', 0.5), ('ref', 0.5)):
            rep(f'C {trig} 損切り{stop}+{buf}', X.run(EV, dict(C0, trig=trig, stop=stop, buf=buf)))
    import fail_ea2 as F2
    FE = F2.events(near=0.7, s200=True, h4p=False, hl=True, win=24)
    F0 = dict(trig='dow', stop='ref', buf=0.3, exit='h1', act=1.0)
    rep('F75 元（M15仮転換）', X.run(FE, F0))
    for trig in ('m5prov', 'm5maj'):
        for stop, buf in (('m5swing', 0.2), ('ref', 0.3)):
            rep(f'F75 {trig} 損切り{stop}+{buf}', X.run(FE, dict(F0, trig=trig, stop=stop, buf=buf)))
