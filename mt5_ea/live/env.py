"""H4 environment filters, ported from research/dow_strategy/env_ctx.py, range_detect.py, triangles.py (detect2) and
gen_tri_intervals.py (2026-10-24).

The research builds these on the FULL H4 history (env_ctx loads H4 'long' without the START cut), so Env uses every M15 bar
it is given (not the Frames cut). Live keeps enough data for the longest look-backs: H4 SMA1200 (daily SMA200) and the range
score's 3000-bar ranks.
  sd  = distance beyond the daily SMA200 (H4 SMA1200) on the trade side (ATR(H4) units)
  er  = H4 efficiency ratio over 200 bars;  sh = distance beyond H4 SMA200;  d75 = distance beyond H4 SMA75
  rs  = range score 0..1 (high = range-like), causal ranks over the past 3000 H4 bars (min 1500)
  tri = an automatic H4/H1 triangle is forming (from the bar that made it known until its breakout bar closed)
"""
import bisect

import numpy as np
import pandas as pd

from .core import TF_LEN, resample
from env_recognition import dow_trend
from env_recognition.pivots import atr


def detect2(df, R, nside=3, shrink=0.6, tol=0.25, W0=3.0, MINSL=0.01, MAXLEN=120):
    """triangles.detect2. A triangle without a breakout inside the data gets end=None (still forming at the last bar)."""
    H, L, C = (df[z].to_numpy(float) for z in 'hlc'); A = atr(df); n = len(df)
    cur = {}; out = []; seen = set(); recent = []
    for e in sorted(R['pivot_events'], key=lambda e: (e['available_idx'], e['idx'])):
        cur[e['id']] = (e['idx'], e['kind'], e['price'])
        if e['id'] not in recent:
            recent = (recent + [e['id']])[-24:]
        if e['action'] != 'confirm':
            continue
        j = e['available_idx']
        piv = sorted(cur[i] for i in recent)
        his = [p for p in piv if p[1] == 'hi'][-nside:]; los = [p for p in piv if p[1] == 'lo'][-nside:]
        if len(his) < nside or len(los) < nside:
            continue
        s0 = min(his[0][0], los[0][0]); k = max(his[-1][0], los[-1][0]); a = A[k]
        if not np.isfinite(a) or a <= 0 or k - s0 > MAXLEN:
            continue

        def tangent(P, upper):
            i0, _, p0 = P[0]; best = None
            for i1, _, p1 in P[1:]:
                sl = (p1 - p0) / (i1 - i0)
                if all(((q - (p0 + sl * (iq - i0))) <= tol * a) if upper else ((p0 + sl * (iq - i0)) - q <= tol * a) for iq, _, q in P):
                    best = sl if best is None else (max(best, sl) if upper else min(best, sl))
            return None if best is None else (i0, p0, best)
        U = tangent(his, True); D = tangent(los, False)
        if U is None or D is None:
            continue
        up = lambda x, U=U: U[1] + U[2] * (x - U[0]); lo = lambda x, D=D: D[1] + D[2] * (x - D[0])
        key = (his[0][0], los[0][0], k)
        if key in seen:
            continue
        w0, wk = (up(s0) - lo(s0)) / a, (up(k) - lo(k)) / a
        if w0 < W0 or wk <= 0 or wk > shrink * w0:
            continue
        tu = sum(abs(q - up(iq)) <= tol * a for iq, _, q in his); td = sum(abs(q - lo(iq)) <= tol * a for iq, _, q in los)
        if max(tu, td) < 3:
            continue
        su, sl_ = U[2] / a, D[2] / a
        if su > MINSL and sl_ > MINSL:
            shape = 'wedge_up'
        elif su < -MINSL and sl_ < -MINSL:
            shape = 'wedge_down'
        elif abs(su) <= MINSL and abs(sl_) <= MINSL:
            continue
        elif su > MINSL or sl_ < -MINSL:
            continue
        else:
            shape = 'flat_top' if abs(su) <= MINSL else 'flat_bottom' if abs(sl_) <= MINSL else 'sym'
        seen.add(key)
        bo, end, apex = 0, None, False
        for x in range(j + 1, min(n, j + MAXLEN)):
            if up(x) - lo(x) <= 0:
                apex = True; break
            if C[x] > up(x):
                bo, end = 1, x; break
            if C[x] < lo(x):
                bo, end = -1, x; break
        if end is None and (apex or j + MAXLEN <= n - 1):
            end = min(n - 1, j + MAXLEN)      # research rule (apex reached or MAXLEN bars passed)
        # otherwise the triangle is still forming at the end of the data: end stays None (active)
        out.append(dict(created=j, end=end, bo=bo, shape=shape, w0=w0, up=U, lo=D, h2=up(k), l2=lo(k)))
    return out


class Env:
    def __init__(self, m15, tfs_tri=('H4',)):
        m15 = m15[['t', 'o', 'h', 'l', 'c']].copy(); m15['t'] = pd.to_datetime(m15.t)
        m15 = m15.drop_duplicates('t').sort_values('t').reset_index(drop=True)
        h4 = resample(m15, 'H4').reset_index(drop=True); self.h4 = h4
        c = pd.Series(h4.c.to_numpy(float)); self.A = atr(h4); self.C4 = list(pd.to_datetime(h4.t) + TF_LEN['H4'])
        self.S1200 = c.rolling(1200).mean().to_numpy(); self.S200 = c.rolling(200).mean().to_numpy()
        self.S75 = c.rolling(75).mean().to_numpy(); self.cv = c.to_numpy()
        self.ER = (c.diff(200).abs() / c.diff().abs().rolling(200).sum()).to_numpy()
        self.R4 = dow_trend.run(h4, 'H4')
        self.RS = self._range_score(h4, c)
        self.TRI = {}
        for tf in tfs_tri:
            df = h4 if tf == 'H4' else resample(m15, 'H1').reset_index(drop=True)
            R = self.R4 if tf == 'H4' else dow_trend.run(df, tf)
            T = pd.to_datetime(df.t); L = TF_LEN[tf]
            self.TRI[tf] = [dict(known=T[x['created']] + L, end=(T[x['end']] + L) if x['end'] is not None else pd.Timestamp.max, w0=x['w0'])
                            for x in detect2(df, R)]

    def _range_score(self, h4, c):
        A = self.A
        s75 = c.rolling(75).mean()
        absdev75 = (np.abs(c - s75) / pd.Series(A)).to_numpy()
        slope75 = (np.abs(s75 - s75.shift(10)) / pd.Series(A)).to_numpy()
        er50 = (c.diff(50).abs() / c.diff().abs().rolling(50).sum()).to_numpy()
        parts = [1 - pd.Series(v).rolling(3000, min_periods=1500).rank(pct=True).to_numpy() for v in (absdev75, slope75, er50)]
        with np.errstate(all='ignore'):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                return np.nanmean(np.vstack(parts), axis=0)

    def tri_active(self, t, tf='H4', wmax=10.0):
        return any(x['known'] <= t < x['end'] and x['w0'] <= wmax for x in self.TRI.get(tf, []))

    def ctx_at(self, t, s):
        k = bisect.bisect_right(self.C4, t) - 1
        return dict(sd=s * (self.cv[k] - self.S1200[k]) / self.A[k], er=self.ER[k], sh=s * (self.cv[k] - self.S200[k]) / self.A[k],
                    d75=s * (self.cv[k] - self.S75[k]) / self.A[k], rs=self.RS[k])

    def ok(self, cfg, t, s):
        """env_ctx.env_ok"""
        if cfg.get('dside') is None and not cfg.get('env') and cfg.get('maxdev') is None and not cfg.get('notri'):
            return True
        x = self.ctx_at(t, s)
        if cfg.get('dside') is not None and not x['sd'] > cfg['dside']:
            return False
        if cfg.get('env') == 'T' and not (x['sd'] > 0 and x['er'] > 0.1):
            return False
        if cfg.get('env') == 'R' and not (x['er'] < 0.08 and x['sh'] < 3):
            return False
        if cfg.get('env') == 'R2' and not (x['rs'] > cfg.get('rs_hi', 0.6) and x['sh'] < 3):
            return False
        if cfg.get('env') == 'T2' and not (x['rs'] < cfg.get('rs_lo', 0.4) and x['sd'] > 0):
            return False
        if cfg.get('maxdev') is not None and abs(x['d75']) > cfg['maxdev']:
            return False
        if cfg.get('notri') and self.tri_active(t, cfg['notri']):
            return False
        return True
