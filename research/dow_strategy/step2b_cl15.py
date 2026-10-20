"""Step 2b: refine the only robust new EA - M15 correction line broken (user-style), M15 Dow turn entry.
Variants: environment (daily side / not stretched / no H4 triangle / one-way ER / range score), waiting window,
stop (correction extreme vs M15 turn swing), exits (H1 trail 1R / 1.5R)."""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
import step2_newea as S2  # noqa: E402
EV = S2.cl15_events()
BASE = dict(trig='dow', stop='m15turn', buf=1.0, exit='h1', act=1.0, dside=0, maxdev=3)
V = {
    'md4ll': ('ll', dict(maxdev=4)),
    'md4tri': dict(maxdev=4, notri='H4'),
    'md4lltri': ('ll', dict(maxdev=4, notri='H4')),
    'md3ll': ('ll', dict(maxdev=3)),
}
V0 = {
    'base': {},
    'notri': dict(notri='H4'),
    'win8': dict(win=8),
    'win2': dict(win=2),
    'act15': dict(act=1.5),
    'ref': dict(stop='ref', buf=0.5),
    'md2': dict(maxdev=2),
    'md4': dict(maxdev=4),
    'nodside': dict(dside=None),
    'envT': dict(env='T'),
    'rsT': dict(env='T2', rs_lo=0.5, dside=None),
    'buf05': dict(buf=0.5),
    'll': 'll',          # only corrections that already made a lower low (user: real selling in the correction)
    'h4w': 'h4w',        # only when the H4 trend points the way of the break
}


def run1(k):
    cfg = dict(BASE)
    ev = EV
    spec = V[k]
    if isinstance(spec, tuple):
        cfg.update(spec[1]); spec = spec[0]
    if spec == 'll' or spec == 'h4w':
        import m15_corr_lines as M
        keep = set()
        for ia, pa, ib, pb, cr, en, kind, broken, ll, h4w in M.lines():
            if broken and en is not None and (ll if spec == 'll' else h4w):
                keep.add(X.CL15[en])
        ev = [e for e in EV if e['t'] in keep]
    else:
        cfg.update(spec)
        if 'win' in spec:
            ev = [dict(e, win=spec['win']) for e in EV]
    tr = X.run(ev, cfg)
    tr.to_csv(S2.OUT / f'cl15_{k}.csv', index=False)
    y = tr.t.dt.year; r = tr.R
    b = [r[(y >= a) & (y <= z)].sum() for a, z in ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]
    w = r > 0; eq = r.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return f"{k:8s} n={len(r):4d} {r.sum():+6.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} DD{dd:6.1f} SL{tr.risk.median() / 1e-4:3.0f}p | " + ' '.join(f'{v:+.1f}' for v in b) + ('  ★' if min(b) > 0 else '')


if __name__ == '__main__':
    with Pool(4) as p:
        for s in p.imap_unordered(run1, list(V)):
            print(s, flush=True)
