"""L / L2: impulse trendline bounce (推進TL反発), ported from research/dow_strategy/tl_ea.py config N2 (2026-10-24).

Line (user style): start A = most extreme swing of the previous 20 (H4) / 40 (H1) bars; the outer tangent over the later
same-kind Dow swings known so far. Good line: angle >= 0.03 ATR per bar, 2nd-point pullback depth 30-85%, line direction ==
that TF's major Dow trend. Touch = a bar reaching the line (within 0.25 ATR) after price moved >= 1 ATR away; the 3rd-4th touch
is the setup. Entry: M15 provisional turn in the line direction within 24 h; stop beyond the M15 turn swing + 1.0 ATR(H1)
(min 10 pips); H1 swing trail from +1R. One position per side. N2: H4 and H1 lines, with the daily side, no H4 triangle.
L2 (XAUUSD): the same trades, minus those with the nearest opposing confirmed H4 swing less than 1 ATR(H1) away (room filter,
research entry_features.py room_h4; applied to the finished trade list like the research).
Note: like the research, the line start A uses the final known version of each pivot; parity test 2 shows the live effect.
"""
import bisect

import numpy as np
import pandas as pd

from ..core import TF_LEN, Frames
from ..env import Env
from env_recognition.pivots import atr

ULOOK = {'H4': 20, 'H1': 40}
MAXLEN = 500
N2 = dict(tfs=('H4', 'H1'), nmin=3, nmax=4, min_angle=0.03, depth=(0.3, 0.85), win=24, buf=1.0, exit='h1', dside=0, notri='H4')
ADOPTED = {'EURUSD': dict(room=None), 'XAUUSD': dict(room=1.0)}


def line_touches(df, R, C, A, tf, band=0.25):
    H, L, Cl = (df[z].to_numpy(float) for z in 'hlc')
    last = {}
    for e in R['pivot_events']:
        last[e['id']] = e
    piv = sorted((e['idx'], e['kind'], e['price'], e['available_idx']) for e in last.values())
    byk = {k: [p for p in piv if p[1] == k] for k in ('hi', 'lo')}
    byk_i = {k: [p[0] for p in v] for k, v in byk.items()}
    n, N = len(df), ULOOK[tf]
    out = []
    for ia, kind, pa, _ in piv:
        up = kind == 'lo'
        j0 = max(0, ia - N)
        if (up and L[j0:ia].size and L[j0:ia].min() < pa) or ((not up) and H[j0:ia].size and H[j0:ia].max() > pa):
            continue
        lo_, hi_ = bisect.bisect_right(byk_i[kind], ia), bisect.bisect_right(byk_i[kind], ia + MAXLEN)
        later = sorted(byk[kind][lo_:hi_], key=lambda p: p[3])
        slope = b = None; q = 0; depth = None; ntouch = 2; away = True
        for j in range(ia + 1, min(n, ia + MAXLEN)):
            while q < len(later) and later[q][3] <= j:
                pb = later[q]; sl = (pb[2] - pa) / (pb[0] - ia)
                if slope is None or (sl < slope if up else sl > slope):
                    if slope is None:
                        seg = H[ia:pb[0] + 1] if up else L[ia:pb[0] + 1]
                        pk = seg.max() if up else seg.min()
                        depth = (pk - pb[2]) / max(1e-9, pk - pa) if up else (pb[2] - pk) / max(1e-9, pa - pk)
                    slope, b = sl, pb
                q += 1
            if (L[j] < pa) if up else (H[j] > pa):
                break
            if slope is None:
                continue
            v = pa + slope * (j - ia)
            if (Cl[j] < v) if up else (Cl[j] > v):
                out.append(dict(kind='break', t=C[j], d='up' if up else 'down', ia=ia, tf=tf, n=ntouch,
                                angle=abs(slope) / A[ia], depth=depth, trend=R['bars'][j][0]))
                break
            bd = band * A[j]
            if not away and ((L[j] - v) if up else (v - H[j])) > A[j]:
                away = True
            if away and j > b[0] + 1 and ((L[j] <= v + bd) if up else (H[j] >= v - bd)):
                ntouch += 1; away = False
                out.append(dict(kind='touch', t=C[j], d='up' if up else 'down', n=ntouch, ia=ia, tf=tf, v=v,
                                angle=abs(slope) / A[ia], depth=depth, trend=R['bars'][j][0]))
    return out


def run(F: Frames, room=None, entry_bar=True, env=None, cfg=N2):
    env = env or Env(F.m15_all)
    A4 = atr(F.h4)
    FR = {'H4': (F.h4, F.R4, F.C4, A4), 'H1': (F.h1, F.R1, F.C1, F.A1)}
    _c4 = pd.Series(F.h4.c.to_numpy(float))
    SMA1200 = _c4.rolling(1200).mean().to_numpy()
    sd = lambda t, s: (lambda k: s * (_c4[k] - SMA1200[k]) / A4[k])(bisect.bisect_right(F.C4, t) - 1)
    M15T = F.M15T; n = F.N; L15 = TF_LEN['M15']
    prov = [e for e in F.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
    turns = {'up': sorted(e['idx'] for e in prov if e['to'] == 'up'), 'down': sorted(e['idx'] for e in prov if e['to'] == 'down')}
    entries = {}
    for tf in cfg['tfs']:
        for e in line_touches(*FR[tf], tf):
            if e['kind'] != 'touch' or not (cfg['nmin'] <= e['n'] <= cfg['nmax']):
                continue
            if e['trend'] != e['d']:
                continue
            if e['angle'] < cfg['min_angle'] or e['depth'] is None or not (cfg['depth'][0] <= e['depth'] <= cfg['depth'][1]):
                continue
            i0 = M15T.searchsorted(e['t']); i1 = M15T.searchsorted(e['t'] + pd.Timedelta(hours=cfg['win']))
            lst = turns[e['d']]; j = bisect.bisect_left(lst, i0)
            if j < len(lst) and lst[j] < i1:
                entries.setdefault(lst[j], []).append((e['d'], tf))
    trades, pos, pending = [], [], []
    h, l, c, o = F.h, F.l, F.c, F.o
    for i in range(n):
        keep = []
        for p in pos:
            if p['k'] > i or (p['k'] == i and not entry_bar):
                keep.append(p); continue
            s = p['side']
            if (l[i] <= p['sl']) if s == 1 else (h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = M15T[i]; p['why'] = 'stop'; trades.append(p); continue
            fav = s * ((h[i] if s == 1 else l[i]) - p['entry'])
            p['mfe'] = max(p.get('mfe', 0.0), fav / p['risk'])
            if not p['trail'] and fav >= 1.0 * p['risk']:
                p['trail'] = True
            if p['trail']:
                v = F.last_swing(F.H1P, F.H1PT, M15T[i] + L15, 'lo' if s == 1 else 'hi')
                if v is not None:
                    v -= s * F.PIP
                    if (v < c[i]) if s == 1 else (v > c[i]):
                        p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in entries or M15T[i] < F.START:
            continue
        k1 = bisect.bisect_right(F.C1, M15T[i] + L15) - 1
        for d, tf in entries[i]:
            s = 1 if d == 'up' else -1
            if any(p['side'] == s for p in pos):
                continue
            if cfg.get('dside') is not None and not sd(M15T[i] + L15, s) > cfg['dside']:
                continue
            if not env.ok({k: cfg.get(k) for k in ('maxdev', 'notri')}, M15T[i] + L15, s):
                continue
            swing = F.R15['prov_bars'][i][1]
            if swing is None:
                continue
            if i + 1 >= n:
                pending.append(dict(signal_t=M15T[i], side=s, ref=swing, buf=cfg['buf'] * F.A1[k1], min_risk=10 * F.PIP, tag=tf)); continue
            entry = o[i + 1]; sl = swing - s * cfg['buf'] * F.A1[k1]
            if s * (entry - sl) < 10 * F.PIP:
                sl = entry - s * 10 * F.PIP
            pos.append(dict(k=i + 1, t=M15T[i + 1], side=s, entry=entry, sl=sl, sl0=sl, risk=s * (entry - sl), trail=False, src=tf, tag=tf))
    tr = pd.DataFrame(trades)
    if len(tr):
        tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - F.COST / tr.risk
    r = dict(trades=tr, open=pos, pending=pending)
    return r if room is None else room_filter(F, r, room)


def room_h4(F: Frames, t, s, entry):
    """entry_features.room_h4: nearest opposing confirmed H4 swing beyond the entry (last 60 swings), in ATR(H1)."""
    piv4 = F.__dict__.get('_piv4')
    if piv4 is None:
        piv4 = F._piv4 = sorted(((F.C4[e['available_idx']], e['kind'], e['price']) for e in F.R4['pivot_events'] if e['action'] == 'confirm'), key=lambda x: x[0])
        F._pt4 = [p[0] for p in piv4]
    k1 = bisect.bisect_right(F.C1, t) - 1
    j = bisect.bisect_right(F._pt4, t) - 1; seen = 0
    while j >= 0 and seen < 60:
        _, kind, pr = piv4[j]
        if (kind == 'hi' and s == 1 and pr > entry) or (kind == 'lo' and s == -1 and pr < entry):
            return abs(pr - entry) / F.A1[k1]
        j -= 1; seen += 1
    return np.nan


def room_filter(F, r, room):
    ok = lambda t, s, e: not (room_h4(F, pd.Timestamp(t), s, e) < room)
    tr = r['trades']
    if len(tr):
        tr = tr[[ok(t, s, e) for t, s, e in zip(tr.t, tr.side, tr.entry)]].reset_index(drop=True)
    return dict(trades=tr, open=[p for p in r['open'] if ok(p['t'], p['side'], p['entry'])], pending=r['pending'])
