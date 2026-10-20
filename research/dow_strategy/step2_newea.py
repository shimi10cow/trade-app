"""Step 2 (2026-10-20): new EA candidates = setup x trigger x stop x environment, all on ea_core (causal).
setups : fib (38/50/62 % pullback of the H4 leg), prot (H4 protected level only), w (trend-end W, H4),
         tri_h1 (H1 triangle broken in the H4 direction), tri_h4 (H4 triangle broken in the D1 direction),
         cl15 (M15 correction line broken, new user-style lines)
trigger: dow (M15 provisional turn) | stoch (existing EA stochastic sequence)
stop   : m15turn / m15swing (by trigger) | h1swing | ref (setup's own structure)
env    : none | dside (daily side) | dside+maxdev3 (not stretched from H4 SMA75)
exit   : H1 swing trail after +1R (the robust default so far)
Writes results/step2_summary.csv (+ trade files for every config). Usage: DT_START=2005-01-01 ... python step2_newea.py"""
import sys, itertools, bisect
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
import setups as SU  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'step2'; OUT.mkdir(exist_ok=True)


def tri_events(tf, higher_ok=True):
    import triangles as TR
    df = TR.FR[tf][0]; T = pd.to_datetime(df.t); L = pd.Timedelta(hours=4 if tf == 'H4' else 1)
    hf = TR.HIGHER[tf]; dfh, Rh = TR.FR[hf]; Ch = list(pd.to_datetime(dfh.t) + (pd.Timedelta(days=1) if hf == 'D1' else pd.Timedelta(hours=4)))
    ev = []
    for x in TR.detect2(tf):
        if not x['bo'] or x['w0'] > 10 or x['shape'].startswith('wedge'):
            continue
        tb = T[x['end']] + L; s = x['bo']
        kh = bisect.bisect_right(Ch, tb) - 1
        if higher_ok and (kh < 0 or Rh['bars'][kh][0] != ('up' if s == 1 else 'down')):
            continue
        ref = x['l2'] if s == 1 else x['h2']                     # opposite line at the last swing
        ev.append(dict(t=tb, side=s, tag='tri', ref=ref, win=24))
    return ev


def cl15_events():
    import m15_corr_lines as M
    ev = []
    for ia, pa, ib, pb, cr, en, kind, broken, ll, h4w in M.lines():
        if not broken or en is None:
            continue
        s = 1 if kind == 'hi' else -1                            # down line over highs broken upward -> buy
        seg = B.l[ia:en + 1] if s == 1 else B.h[ia:en + 1]
        ref = seg.min() if s == 1 else seg.max()                 # the correction's extreme
        ev.append(dict(t=X.CL15[en], side=s, tag='cl15', ref=ref, win=4))
    return ev


SETUPS = {'fib': SU.fib_pullback, 'prot': SU.protected_retest, 'w': SU.w_trend_end,
          'tri_h1': lambda: tri_events('H1'), 'tri_h4': lambda: tri_events('H4'), 'cl15': cl15_events}
EV = {}


def cfgs():
    for su, trig, stop, env in itertools.product(SETUPS, ('dow', 'stoch'), ('turn', 'h1swing', 'ref'), ('none', 'dside', 'dside_md')):
        st = ('m15turn' if trig == 'dow' else 'm15swing') if stop == 'turn' else stop
        yield dict(setup=su, trig=trig, stop=st, envn=env, buf=1.0 if st.startswith('m15') else 0.5,
                   dside=None if env == 'none' else 0, maxdev=3 if env == 'dside_md' else None)


def run1(c):
    if c['setup'] not in EV:
        EV[c['setup']] = SETUPS[c['setup']]()
    ev = EV[c['setup']]
    if c['setup'] == 'fib':
        ev = [e for e in ev if e['tag'] in ('fib382', 'fib500', 'fib618')]
    tr = X.run(ev, dict(trig=c['trig'], stop=c['stop'], buf=c['buf'], exit='h1', act=1.0, dside=c['dside'], maxdev=c['maxdev']))
    key = f"{c['setup']}_{c['trig']}_{c['stop']}_{c['envn']}"
    if len(tr):
        tr.to_csv(OUT / f'{key}.csv', index=False)
    y = tr.t.dt.year if len(tr) else pd.Series(dtype=int)
    r = tr.R if len(tr) else pd.Series(dtype=float)
    b = [r[(y >= a) & (y <= z)].sum() for a, z in ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]
    w = r > 0; eq = r.cumsum().to_numpy(); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min() if len(eq) else 0
    return dict(key=key, **{k: c[k] for k in ('setup', 'trig', 'stop', 'envn')}, n=len(r), sumR=r.sum(), PF=r[w].sum() / max(1e-9, -r[~w].sum()),
                DD=dd, risk_pips=(tr.risk.median() / 1e-4 if len(tr) else np.nan), b1=b[0], b2=b[1], b3=b[2], b4=b[3], b5=b[4], allpos=min(b) > 0)


if __name__ == '__main__':
    C = list(cfgs())
    C.sort(key=lambda c: c['setup'])                                   # same setup -> same worker cache more often
    with Pool(4) as pool:
        rows = []
        for r in pool.imap_unordered(run1, C, chunksize=3):
            rows.append(r)
            print(f"{r['key']:36s} n={r['n']:4d} {r['sumR']:+7.1f}R PF{r['PF']:.2f} DD{r['DD']:6.1f} SL{r['risk_pips']:4.0f}p | "
                  f"{r['b1']:+.1f} {r['b2']:+.1f} {r['b3']:+.1f} {r['b4']:+.1f} {r['b5']:+.1f}{'  ★' if r['allpos'] else ''}", flush=True)
    pd.DataFrame(rows).to_csv(B.HERE / 'results' / 'step2_summary.csv', index=False)
