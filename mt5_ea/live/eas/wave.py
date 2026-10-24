"""T2 axis filter (横軸), ported from research/dow_strategy/wave_features.py + gen_pbcount.Pushes (RESEARCH_LOG §61) (2026-10-24).

Skip a T trade when the H4 trend has already made its 3rd or later push (new extreme after a confirmed pullback since the
H4 major Dow turn) AND the H1 correction before the entry took less than 0.7 x the time of the impulse before it.
Impulse = last confirmed H1 swing in the trade direction back to the opposite swing before it; correction = that swing to the
entry. Applied to the finished T trade list, like the research (regime2_T1t.csv -> regime2_T1t_axis.csv).
"""
import numpy as np
import pandas as pd

from ..core import Frames


class Pushes:
    def __init__(self):
        self.side, self.start, self.n, self.ext, self.armed = 0, 0, 0, None, False

    def step(self, i, side, hi, lo, conf):
        if side != self.side:
            self.side, self.start, self.n, self.armed = side, i, 0, False
            self.ext = hi if side == 1 else lo
        for e in conf:
            if e['idx'] > self.start and (e['kind'] == 'lo') == (self.side == 1):
                self.armed = True
        if self.side == 1 and hi > self.ext:
            self.ext = hi; self.n += self.armed; self.armed = False
        elif self.side == -1 and lo < self.ext:
            self.ext = lo; self.n += self.armed; self.armed = False
        return [int(self.side), int(self.n)]


class Axis:
    def __init__(self, F: Frames):
        h1 = F.h1.reset_index(drop=True); h4 = F.h4.reset_index(drop=True)
        self.C1 = np.array(F.C1, dtype='datetime64[ns]'); self.C4 = np.array(F.C4, dtype='datetime64[ns]')
        self.P = sorted(((F.C1[e['available_idx']], e['kind'], e['price'], e['idx']) for e in F.R1['pivot_events'] if e['action'] == 'confirm'), key=lambda x: x[0])
        self.PT = np.array([p[0] for p in self.P], dtype='datetime64[ns]')
        conf4 = {}
        for e in F.R4['pivot_events']:
            if e['action'] == 'confirm':
                conf4.setdefault(e['available_idx'], []).append(e)
        maj4 = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in F.R4['bars']]
        PU = Pushes(); self.st4 = [PU.step(i, maj4[i], h4.h[i], h4.l[i], conf4.get(i, [])) for i in range(len(h4))]

    def features(self, t, s, entry):
        tt = np.datetime64(pd.Timestamp(t)); k1 = np.searchsorted(self.C1, tt, 'right') - 1; k4 = np.searchsorted(self.C4, tt, 'right') - 1
        if k1 < 80 or k4 < 0:
            return None
        P = self.P; j = np.searchsorted(self.PT, tt, 'right') - 1
        want = 'hi' if s == 1 else 'lo'
        while j >= 0 and P[j][1] != want:
            j -= 1
        if j < 1:
            return None
        ext_p, ext_i = P[j][2], P[j][3]
        jj = j - 1
        while jj >= 0 and P[jj][1] == want:
            jj -= 1
        if jj < 0:
            return None
        org_p, org_i = P[jj][2], P[jj][3]
        imp = s * (ext_p - org_p); imp_h = max(1, ext_i - org_i); cor_h = max(1, k1 - ext_i)
        if imp <= 0:
            return None
        sd, n4 = self.st4[k4]
        return dict(t_ratio=cor_h / imp_h, h4_major_push=(n4 if sd == s else -1))

    def keep(self, t, s, entry):
        f = self.features(t, s, entry)
        return f is None or not (f['h4_major_push'] >= 3 and f['t_ratio'] < 0.7)


def axis_filter(F: Frames, r):
    ax = Axis(F)
    tr = r['trades']
    if len(tr):
        tr = tr[[ax.keep(t, s, e) for t, s, e in zip(tr.t, tr.side, tr.entry)]].reset_index(drop=True)
    keep = lambda p: ax.keep(p['t'], p['side'], p['entry'])
    return dict(trades=tr, open=[p for p in r['open'] if keep(p)], pending=[p for p in r['pending'] if keep(p)])
