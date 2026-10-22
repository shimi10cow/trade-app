"""Specialised EAs from the user's marks (USDJPY 2010/2019/2026, 2026-10-21).
Pullback counter (calibrated to the marks): side = H1 provisional Dow trend; reset when the side flips or H1 closes beyond
SMA75 against the side; a pullback counts once it is >= K x ATR(H1) deep from the running extreme; current pullback
number = pushes since reset + 1.
  P (押し目)  : setup when the n-th qualifying pullback appears (n <= maxn), optional SMA20/75 same side, optional 'near
                SMA20' (low within z x ATR of SMA20); trigger = M15 provisional turn back to the trend within `win` hours.
  BO (ブレイク): H1 major Dow turn (or provisional turn) while SMA20/75 is still against it (before the cross).
Stop beyond the M15 turn / H1 swing + buf x ATR(H1); exit = H1 swing trail from +act R (ea_core). Cost 1.2 pip.
Design 2005-2015, check 2016-2026. Usage: python dow_strategy/pb_ea.py [P|BO|all]"""
import sys, json, os, itertools
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ea_core as X  # noqa: E402
B = X.B
OUT = B.HERE / 'results' / 'pb'; OUT.mkdir(exist_ok=True, parents=True)
X.add_trigger('now', lambda: {d: list(range(X.N)) for d in ('up', 'down')})
H1 = B.h1.reset_index(drop=True)
hh, ll, cc = (H1[z].to_numpy(float) for z in 'hlc')
A1 = np.asarray(B.A1)
M20 = H1.c.rolling(20).mean().to_numpy(); M75 = H1.c.rolling(75).mean().to_numpy()
PRV = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R1['prov_bars']]
MAJ = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in B.R1['bars']]
CL = B.C1


def counter(K=2.0):
    """per H1 bar: (side, pushes, in_pullback, pullback_start_flag)"""
    side, n, armed, ext = 0, 0, False, hh[0]; out = []
    for i in range(len(H1)):
        s = PRV[i]
        if s != side or (np.isfinite(M75[i]) and s * (cc[i] - M75[i]) < 0):
            side, n, armed = s, 0, False; ext = hh[i] if s == 1 else ll[i]
        new = False
        dep = (ext - ll[i]) if side == 1 else (hh[i] - ext)
        if not armed and side != 0 and dep >= K * A1[i]:
            armed = True; new = True
        if side == 1 and hh[i] > ext:
            ext = hh[i]; n += armed; armed = False
        elif side == -1 and ll[i] < ext:
            ext = ll[i]; n += armed; armed = False
        out.append((side, n, armed, new))
    return out


CNT = {}


def ev_pullback(maxn=2, minn=1, K=2.0, ma=True, near=None, win=24, d75=None, maj=False):
    if K not in CNT:
        CNT[K] = counter(K)
    st = CNT[K]; ev = []
    for i, (s, n, armed, new) in enumerate(st):
        if not new or s == 0:
            continue
        num = n + 1
        if num < minn or num > maxn:
            continue
        if ma and not (np.isfinite(M20[i]) and np.sign(M20[i] - M75[i]) == s):
            continue
        if maj and MAJ[i] != s:
            continue
        if d75 is not None and not (np.isfinite(M75[i]) and s * (cc[i] - M75[i]) >= d75 * A1[i]):
            continue
        if near is not None:
            ext = ll[i] if s == 1 else hh[i]
            if s * (ext - M20[i]) > near * A1[i]:
                continue
        ev.append(dict(t=CL[i], side=s, tag=f'P{num}', win=win))
    return ev


def ev_break(kind='major', win=12):
    ev = []
    src = B.R1['events'] if kind == 'major' else B.R1['prov_events']
    for e in src:
        if kind == 'major' and not (e.get('machine') == 'major' and e.get('action') == 'REVERSAL'):
            continue
        if kind == 'prov' and e.get('action') not in ('REVERSAL',):
            continue
        i = e['idx']; s = 1 if e.get('to') == 'up' else -1
        if not np.isfinite(M20[i]) or np.sign(M20[i] - M75[i]) == s:
            continue  # only before the SMA20/75 cross
        if kind == 'prov' and MAJ[i] == s:
            continue
        ev.append(dict(t=CL[i], side=s, tag='BO' + kind, win=win))
    return ev


def marks():
    f = os.environ.get('MARKS')
    if not f:
        return None
    M = pd.read_pickle(f); sc = float(os.environ.get('MARK_SCALE', '1'))
    M = M.assign(tt=pd.to_datetime(M.t, unit='s'))
    return M


MK = marks()


def coverage(tr):
    if MK is None or not len(tr):
        return ''
    hit = []
    for m in MK.itertuples():
        x = tr[(tr.side == m.side) & ((tr.t - m.tt).abs() <= pd.Timedelta(hours=12))]
        hit.append(len(x) > 0)
    MK['hit'] = hit
    g = MK.groupby(MK.label.replace({'3': '3+', '4': '3+'})).hit.mean()
    return f"印拾い {np.mean(hit):.0%} (" + ' '.join(f'{k}:{v:.0%}' for k, v in g.items()) + ')'


def stats(tr):
    y = tr.t.dt.year; r = tr.R
    def st(m):
        rr = r[m]; w = rr > 0
        return len(rr), rr.sum(), rr[w].sum() / max(1e-9, -rr[~w].sum())
    a = st((y >= 2005) & (y <= 2015)); b = st((y >= 2016) & (y <= 2026))
    eq = r[y >= 2005].cumsum(); dd = (eq - eq.cummax()).min()
    return f"前半 {a[0]:4d}回 {a[1]:+6.1f}R PF{a[2]:.2f} | 後半 {b[0]:4d}回 {b[1]:+6.1f}R PF{b[2]:.2f} | DD{dd:6.1f}"


def run_one(spec):
    name, kind, kw, cfg = spec
    tr = X.run((ev_pullback if kind == 'P' else ev_break)(**kw), cfg)
    tr = tr[tr.t.dt.year >= 2005] if len(tr) else tr
    tr.to_csv(OUT / f'{name}.csv', index=False)
    return name, stats(tr) + ' ' + coverage(tr)


def specs(which):
    S = []
    if which in ('P', 'all'):
        for maxn, ma, near, stop, buf in itertools.product((1, 2, 3), (True, False), (None, 0.5), ('m15turn', 'h1swing'), (0.3,)):
            S.append((f'P_n{maxn}_ma{int(ma)}_nr{near}_{stop}', 'P', dict(maxn=maxn, ma=ma, near=near),
                      dict(trig='dow', stop=stop, buf=buf, exit='h1', act=1.0)))
    if which == 'P2':
        for maxn, d75, stop in itertools.product((2, 3, 9), (1.0, 1.7, 2.5, 3.0), ('m15turn', 'h1swing')):
            S.append((f'P2_n{maxn}_d{d75}_{stop}', 'P', dict(maxn=maxn, ma=True, d75=d75),
                      dict(trig='dow', stop=stop, buf=0.3, exit='h1', act=1.0)))
    if which == 'P3':
        for d75, trig, stop in itertools.product((1.7, 2.5), ('dow', 'stoch', 'now'), ('m15swing', 'h1swing')):
            S.append((f'P3_d{d75}_{trig}_{stop}', 'P', dict(maxn=3, ma=True, d75=d75, win=24),
                      dict(trig=trig, stop=stop, buf=0.3, exit='h1', act=1.0)))
    if which == 'P4':
        for maj, rs in itertools.product((False, True), (None, 0.4, 0.5)):
            cfg = dict(trig='dow', stop='h1swing', buf=0.3, exit='h1', act=1.0)
            if rs: cfg.update(env='T2', rs_lo=rs)
            S.append((f'P4_maj{int(maj)}_rs{rs}', 'P', dict(maxn=3, ma=True, d75=2.5, maj=maj), cfg))
    if which in ('BO', 'all'):
        for kind, trig, stop in itertools.product(('major', 'prov'), ('now', 'dow'), ('m15turn', 'h1swing')):
            S.append((f'BO_{kind}_{trig}_{stop}', 'BO', dict(kind=kind),
                      dict(trig=trig, stop=stop, buf=0.3, exit='h1', act=1.0, win=12)))
    return S


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    with Pool(int(os.environ.get('NPROC', '4'))) as p:
        for name, s in p.imap_unordered(run_one, specs(which)):
            print(f'{name:34s} {s}', flush=True)
