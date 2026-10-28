"""DS width study: same setups as mt5_ea/live/eas/ds.py, plus the times of the left shoulder / neck / right shoulder."""
import sys, bisect, time, zipfile, io
sys.path.insert(0, '/home/user/trade-app')
import numpy as np, pandas as pd
from mt5_ea.live.core import Frames, to_space
from mt5_ea.live.eas import ds as DS
from mt5_ea.live import engine as E
R = '/home/user/trade-app/'
def load(sym):
    if sym == 'XAUUSD':
        z = zipfile.ZipFile(R + 'research/data/XAUUSD2003.M5.zip'); d = pd.read_csv(z.open(z.namelist()[0]), dtype={'<TIME>': str})
        d = pd.DataFrame(dict(time=pd.to_datetime(d['<DTYYYYMMDD>'].astype(str) + d['<TIME>'].str.zfill(4), format='%Y%m%d%H%M'), open=d['<OPEN>'], high=d['<HIGH>'], low=d['<LOW>'], close=d['<CLOSE>']))
        d = d.set_index('time').resample('15min', label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna().reset_index()
        start = '2005-01-01'
    else:
        d = pd.read_csv(R + f'{sym}Cash#_M15_MT5.csv', usecols=[0, 1, 2, 3, 4], encoding='utf-8-sig', parse_dates=['time'])
        d = d[d.time >= '2016-10-27 01:15'].reset_index(drop=True); start = '2017-12-01'
    m = pd.DataFrame(dict(t=d.time, o=to_space(sym, d.open), h=to_space(sym, d.high), l=to_space(sym, d.low), c=to_space(sym, d.close)))
    return m, start
def setups_w(F, tf='H1'):
    """copy of DS.setups (same logic) that also keeps the left shoulder / neck times"""
    CL15 = F.CL15; Mh, Ml, Mc = F.h, F.l, F.c
    TURN = {d: sorted(e['idx'] for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d) for d in ('up', 'down')}
    df = F.h1.reset_index(drop=True); hi, lo = df.h.to_numpy(float), df.l.to_numpy(float); T1 = pd.DatetimeIndex(df.t)
    ev = []
    evs = DS._events(F, tf)
    # left shoulder time: recompute the extreme bar of the run that ended at te
    tr = [b[0] for b in F.R1['bars']]; close = pd.DatetimeIndex(F.C1); runs = {}; k0 = 0
    for k in range(1, len(df)):
        if tr[k] != tr[k - 1]:
            start = k0; k0 = k
            seg = slice(start, k + 1); s = -1 if tr[k - 1] == 'up' else 1
            j = start + (int(np.argmax(hi[seg])) if s == -1 else int(np.argmin(lo[seg])))
            runs[close[k]] = (T1[j], T1[start])
    for e in evs:
        s, Hx = e['side'], e['H']; i0 = CL15.searchsorted(e['te']); iend = min(CL15.searchsorted(e['te'] + pd.Timedelta('120h')), len(Mc))
        Lx = None; rally = None; ineck = None
        for i in range(i0, iend):
            if (Mh[i] > Hx) if s == -1 else (Ml[i] < Hx):
                break
            if rally is None:
                newL = (Ml[i] if s == -1 else Mh[i]) if Lx is None else (min(Lx, Ml[i]) if s == -1 else max(Lx, Mh[i]))
                if Lx is None or newL != Lx: ineck = i
                Lx = newL; rng = abs(Hx - Lx)
                if rng > 0 and ((Mh[i] - Lx) if s == -1 else (Lx - Ml[i])) >= 0.38 * rng:
                    rally = i
                continue
            lst = TURN['down' if s == -1 else 'up']; k = bisect.bisect_left(lst, rally)
            if k < len(lst) and lst[k] < iend:
                j = lst[k]; seg = Mh[i0:j + 1] if s == -1 else Ml[i0:j + 1]
                if (seg.max() > Hx) if s == -1 else (seg.min() < Hx):
                    break
                sh = Mh[rally:j + 1].max() if s == -1 else Ml[rally:j + 1].min(); retr = abs(sh - Lx) / rng
                tag = f"{tf}|{retr:.2f}|{rng / e['a4']:.2f}|{e['res']}|{(CL15[j] - e['te']) / pd.Timedelta('1h'):.0f}"
                tl, trun = runs.get(e['te'], (pd.NaT, pd.NaT))
                ev.append(dict(t=CL15[j], side=s, ref_sh=sh, ref_H=Hx, neck=Lx, win=0.3, tag=tag, t_left=tl, t_neck=F.T15.iloc[ineck], t_rev=e['te']))
            break
    return ev
out = []
for sym in sys.argv[1:]:
    t0 = time.time(); m, start = load(sym); F = Frames(m, start); a = DS.ADOPTED[sym]
    evs = setups_w(F)
    chk = DS.setups(F); assert [(e['t'], e['tag']) for e in chk] == [(e['t'], e['tag']) for e in evs], 'setup copy differs'
    r = DS.run_variant(F, 'H1', a['stop'], a['exit'], events=evs)['trades']
    meta = pd.DataFrame(evs)[['t', 't_left', 't_neck', 't_rev']].rename(columns={'t': 'setup_t'})
    r = r.merge(meta, on='setup_t', how='left')
    r['adopted'] = [DS.adopted_filter(dict(tag=t, side=s), a['side']) for t, s in zip(r.tag, r.side)]
    r['depth'] = [float(t.split('|')[2]) for t in r.tag]
    r['sym'] = sym; out.append(r); print(sym, len(r), 'trades', f'{time.time() - t0:.0f}s', flush=True)
pd.concat(out).to_pickle('/tmp/claude-0/-home-user-trade-app/13978ff6-6519-5f05-b953-f01dd0dd89a9/scratchpad/ds/dsall_trades_' + '_'.join(sys.argv[1:]) + '.pkl')
