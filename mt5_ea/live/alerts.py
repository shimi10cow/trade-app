"""Discretionary alerts (2026-11-21): 'そろそろ' notices for the trader's own setups, wider than the EAs. No orders, ever.

The trader keeps several alert profiles in the app (demo config 'alerts': {on, profiles: [...]}). A profile =
  scenes   gateway  (出入口, methods 1 / 6) = the last protected swing broken by an H4 major reversal
           fortress (砦,     methods 2 / 7) = the protected swing of the current H4 major trend (breakout_protect)
           band     (抵抗体)              = an H4 level where >= 2 H4 swings sit within 0.25 ATR (90 days), either side
  touch    an M15 bar back within `near` ATR(H4) of the line after an M15 close >= `away` ATR beyond it; every return counts
           (2026-11-21), the line ends after `life` days or when an H4 close goes `brk` ATR through it (default 0 = any close beyond)
  timing   (what sends the alert after the touch; 2026-11-21 user: not the touch itself, too many)
           turn  = the first M15 Dow turn toward the bounce within 12 hours (the EAs' confirmation)
           stm15 = M15 stochastic (14,5,3): %K below 20 -> %K crosses %D up -> %K back above 20 (sell: 80), within 12 hours
           sth1  = the same on H1, within 48 hours (same rule as the app's reservations, reservations.trigger_on_last)
  conds    a catalog (CATALOG below, the app shows the same list): each on / off with its numbers
  pairs    [] = all FX pairs
Every new M15 bar the PC scans the pairs (last 400 days of MT5 bars), evaluates every profile that is on, sends new alerts
to Telegram and to GAS (eaAlert -> sheet EA_Alerts, shown in the app). The settings come back from GAS on every call.
Run (desktop, its own window, read only): ALERTS_START.bat -> python -m mt5_ea.live.alerts
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from mt5_ea.live.core import Frames
from mt5_ea.live.eas import dsc
from mt5_ea.live.reservations import stoch

PAIRS = ('EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'USDCAD', 'AUDUSD', 'NZDUSD', 'EURJPY', 'GBPJPY', 'AUDJPY', 'NZDJPY', 'CADJPY', 'CHFJPY',
         'AUDCAD', 'AUDCHF', 'AUDNZD', 'CADCHF', 'EURAUD', 'EURNZD', 'GBPAUD', 'GBPCAD', 'GBPCHF', 'GBPNZD', 'NZDCAD', 'NZDCHF')
DAYS, WARM = 400, 250
DAY = np.timedelta64(1, 'D'); HOUR = np.timedelta64(1, 'h'); M15 = np.timedelta64(15, 'm')
ALERTS_V = 5                  # 2026-11-21: settings version (2 = methods 1 / 2 / 6 / 7 presets); older saved profiles are replaced
SCENE_JA = {'gateway': '出入口', 'fortress': '砦', 'band': '抵抗体'}

# condition catalog: key -> (label, {param: default}); the app (ea_live.js ALERT_CAT) shows the same keys / labels / params
CATALOG = {
    'h4dir':   ('H4 の本転換の向きと同じ', {}),
    'prov':    ('H4 の仮のダウが逆向きでない', {}),
    'd1ma':    ('日足の MA が進行方向で、値段がその向こう側', {'period': 75, 'slope': 10}),
    'd1ma_x':  ('日足が〇でない（手法 6・7：日足の MA が進行方向・値段が向こう側、がそろっていない）', {'period': 75, 'slope': 10}),
    'd1dow':   ('日足のダウ（直近の山・谷 2 つずつ）が逆でない', {}),
    'h4ma':    ('H4 の MA が進行方向', {'period': 20, 'slope': 3}),
    'h1ma':    ('H1 の MA が進行方向で、値段がその向こう側', {'period': 75, 'slope': 5}),
    'h1ma2':   ('H1 の MA（2 本目）が進行方向', {'period': 20, 'slope': 3}),
    'h1order': ('H1 の MA の並び（短い方が進行方向側）', {'fast': 20, 'slow': 75}),
    'touch':   ('線に H4 の山谷が N 個以上（反発の回数）', {'n': 2, 'width': 0.25, 'days': 90}),
    'imp4':    ('H4 の推進線が効いている（押しが推進線の近く）', {'atr': 1.0}),
    'impd':    ('日足の推進線が効いている', {}),
    'impany':  ('推進トレンドライン（H4 か日足のどちらか）が効いている', {}),
    'noimpbrk': ('H4 の推進線を割っていない', {}),
    'noopp':   ('反対向きの H4 推進線が残っていない', {}),
    'ctr4':    ('H4 の逆トレンドライン（調整線）を抜けている', {}),
    'ctr1':    ('H1 の逆トレンドラインを抜けている', {}),
    'ctr15':   ('M15 のトレンドライン（調整線）を抜けている', {}),
    'ctr41':   ('調整トレンドライン（H1 か H4 のどちらか）を抜けている', {}),
    'uscore':  ('あなたの点数（線＋推進TL＋MA＋調整TL＋M15TL）が N 点以上', {'n': 4, 'line': 1, 'imp': 2, 'ma': 1, 'ctr': 1, 'm15': 1}),
    'score':   ('D の点数（EA の線の点数）が N 以上', {'n': 2}),
    'run':     ('直前に伸びすぎていない（H1 の n 本で x ATR 未満）', {'bars': 24, 'atr': 3.0}),
    'madist':  ('H4 の MA から離れすぎていない', {'period': 75, 'atr': 2.0}),
    'depth':   ('押しの深さ（直近の H4 の波に対して）', {'min': 0.1, 'max': 0.382}),
    'days':    ('H4 の本転換からの日数', {'min': 0, 'max': 30}),
    'hours':   ('時間帯（日本時間、何時から何時まで）', {'from': 8, 'to': 26}),
}

PRESETS = [   # 2026-11-21 (user): only the trader's own methods 1 / 2 / 6 / 7; the alert comes when entering (M15 Dow turn after the touch);
              # + the trader's score (line 1 + impulse TL 2 + H1 MA 1 + correction TL 1 + M15 TL 1) >= 4 (user: selectable, threshold editable)
    dict(id='m1', name='手法1：日足〇・H4 出入口', on=True, scenes=['gateway'], timing='zone', near=0.3, away=1.0, life=30, brk=0.0, pairs=[],
         conds={'h4dir': {}, 'd1ma': {'period': 75, 'slope': 10}, 'uscore': {'n': 4, 'line': 1, 'imp': 2, 'ma': 1, 'ctr': 1, 'm15': 1}}),
    dict(id='m2', name='手法2：日足〇・H4 砦', on=True, scenes=['fortress'], timing='zone', near=0.3, away=1.0, life=30, brk=0.0, pairs=[],
         conds={'h4dir': {}, 'd1ma': {'period': 75, 'slope': 10}, 'uscore': {'n': 4, 'line': 1, 'imp': 2, 'ma': 1, 'ctr': 1, 'm15': 1}}),
    dict(id='m6', name='手法6：日足✕・H4 出入口', on=True, scenes=['gateway'], timing='zone', near=0.3, away=1.0, life=30, brk=0.0, pairs=[],
         conds={'h4dir': {}, 'd1ma_x': {'period': 75, 'slope': 10}, 'uscore': {'n': 4, 'line': 1, 'imp': 2, 'ma': 1, 'ctr': 1, 'm15': 1}}),
    dict(id='m7', name='手法7：日足✕・H4 砦', on=True, scenes=['fortress'], timing='zone', near=0.3, away=1.0, life=30, brk=0.0, pairs=[],
         conds={'h4dir': {}, 'd1ma_x': {'period': 75, 'slope': 10}, 'uscore': {'n': 4, 'line': 1, 'imp': 2, 'ma': 1, 'ctr': 1, 'm15': 1}}),
]


def space(sym, px):
    return np.asarray(px, float) / (100.0 if sym.endswith('JPY') else 1.0)


class Market:
    """One symbol: frames + everything the conditions need, computed once per scan."""

    def __init__(self, sym, m):
        self.sym = sym; self.k = 100.0 if sym.endswith('JPY') else 1.0
        m = m[['t', 'o', 'h', 'l', 'c']].copy(); m['t'] = pd.to_datetime(m.t).astype('datetime64[us]')
        for z in 'ohlc':
            m[z] = space(sym, m[z].to_numpy())
        self.start = m.t.iat[0] + pd.Timedelta(days=WARM)
        self.F = F = Frames(m, self.start, h_days=WARM, m_days=WARM); self.cx = cx = dsc._Ctx(F)
        self.TM, self.MH, self.ML, self.MC, self.C4 = cx.TM, cx.MH, cx.ML, cx.MC, cx.C4; self.CL = self.TM + M15
        self.P4 = cx.raw['H4']; self.P15 = cx.raw['M15']
        pv = sorted((self.C4[e['idx']], e['to']) for e in F.R4['all_events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL')
        self.pv = pv; self.pvt = np.array([a for a, _ in pv], dtype='datetime64[ns]')
        self.prv = cx.PV; self.prvt = np.array([a for a, _ in cx.PV], dtype='datetime64[ns]')
        self.d1c = pd.Series(cx.cd); self.h4c = pd.Series(cx.c4); self.h1c = pd.Series(cx.c1); self._ma = {}; self._st = {}

    def ma(self, tf, n):
        key = (tf, n)
        if key not in self._ma:
            self._ma[key] = {'D1': self.d1c, 'H4': self.h4c, 'H1': self.h1c}[tf].rolling(int(n)).mean().to_numpy()
        return self._ma[key]

    def a4(self, t):
        return self.cx.a4[max(0, int(np.searchsorted(self.C4, t, side='right')) - 1)]

    def h4dir(self, t):
        j = int(np.searchsorted(self.pvt, t, side='right')) - 1
        return 0 if j < 0 else (1 if self.pv[j][1] == 'up' else -1)

    # -- the lines and the moments price comes back to them
    def lines(self, scenes, life):
        cx, F = self.cx, self.F; out = []; seen = set()
        for e in F.R4['all_events']:
            if e.get('machine') != 'major':
                continue
            if 'gateway' in scenes and e['action'] == 'REVERSAL' and e.get('broken_price') is not None:
                out.append(('gateway', 1 if e['to'] == 'up' else -1, float(e['broken_price']), self.C4[e['idx']], life))
            elif 'fortress' in scenes and e.get('action') == 'breakout_protect':
                s, L = (1 if e['trend'] == 'up' else -1), float(e['prot_price'])
                if (round(L, 6), s) not in seen:
                    seen.add((round(L, 6), s)); out.append(('fortress', s, L, self.C4[e['idx']], life))
        if 'band' in scenes:                    # >= 2 H4 swings within 0.25 ATR (90 days): a level for either side
            c4, k4, p4 = self.P4[0], self.P4[1], self.P4[2]; o = np.argsort(c4); have = []
            for ii, i in enumerate(o):
                A = self.a4(c4[i]); prev = [j for j in o[:ii] if c4[i] - c4[j] <= 90 * DAY and abs(p4[j] - p4[i]) <= 0.25 * A]
                if not prev:
                    continue
                L = float(np.mean([p4[j] for j in prev] + [p4[i]]))
                if any(abs(L - x) <= 0.25 * A and c4[i] - tb <= life * DAY for x, tb in have):
                    continue
                have.append((L, c4[i])); out += [('band', 1, L, c4[i], life), ('band', -1, L, c4[i], life)]
        return out

    def touches(self, L, s, t0, life, near, away, brk=0.0):
        """2026-11-21 (user): every return to the line, not only the first. A touch = an M15 bar within `near` ATR of the line after
        an M15 close >= `away` ATR beyond it (on the trade side); after a touch price must go `away` beyond again before the next one.
        The line ends after `life` days or when an H4 close goes more than `brk` ATR through it. Returns [(bar index, touch number)]."""
        TM, MC, MH, ML = self.TM, self.MC, self.MH, self.ML; A = self.a4(t0)
        q0 = int(np.searchsorted(TM, t0)); q1 = int(np.searchsorted(TM, t0 + int(life) * DAY))
        k0 = int(np.searchsorted(self.C4, t0, side='right')); k1 = int(np.searchsorted(self.C4, t0 + int(life) * DAY))
        thr = np.nonzero(s * (self.cx.c4[k0:k1] - L) < -brk * A)[0]
        if len(thr):                            # the H4 close that ends the line (its bar closes at C4[...])
            q1 = min(q1, int(np.searchsorted(TM, self.C4[k0 + thr[0]])))
        out, armed, n = [], False, 0
        for q in range(q0, min(q1, len(TM))):
            if not armed:
                if s * (MC[q] - L) >= away * A:
                    armed = True
                continue
            if s * ((ML[q] if s > 0 else MH[q]) - L) <= near * A:
                n += 1; out.append((q, n)); armed = False
        return out, A

    def stoch_after(self, q, L, s, A, tf):
        """the stochastic trigger (as the reservations) after the touch: (close time, close price) or None"""
        cx = self.cx
        if tf not in self._st:
            if tf == 'M15':
                self._st[tf] = (stoch(self.MH, self.ML, self.MC), self.CL, self.MC, self.MH, self.ML)
            else:
                self._st[tf] = (stoch(cx.H1h, cx.H1l, cx.c1), np.asarray(cx.C1, dtype='datetime64[ns]'), cx.c1, cx.H1h, cx.H1l)
        (k, d), CT, CC, HH, LL = self._st[tf]
        i0 = max(1, int(np.searchsorted(CT, self.CL[q]))); n = 48; state = 0; zone = 20.0 if s > 0 else 80.0
        for i in range(i0, min(i0 + n, len(CT))):
            if s * (CC[i] - L) < -0.4 * A:
                return None
            pk, pd_, kk, dd = k[i - 1], d[i - 1], k[i], d[i]
            if np.isnan([pk, pd_, kk, dd]).any():
                continue
            if state == 0 and s * (zone - kk) > 0:
                state = 1
            elif state == 1 and s * (pk - pd_) <= 0 and s * (kk - dd) > 0:
                state = 2
            elif state == 2 and s * (zone - pk) >= 0 and s * (kk - zone) > 0:
                return CT[i], float(CC[i])
        return None

    def turn_after(self, q, L, s, A, n=48, stop=0.4):
        """first M15 Dow turn toward the bounce within n bars (12 hours) of the touch (bar index), or None.
        stop: give up once an M15 close is this many ATR through the line (None = never)."""
        c15, k15, p15, t15 = self.P15; TM, MC, CL = self.TM, self.MC, self.CL
        for k in range(q, min(q + n, len(TM))):
            if stop is not None and s * (MC[k] - L) < -stop * A:
                return None
            m = (c15 <= CL[k])
            lo = np.nonzero(m & (t15 >= TM[q] - 2 * HOUR) & (k15 == ('lo' if s > 0 else 'hi')))[0]
            hi = np.nonzero(m & (k15 == ('hi' if s > 0 else 'lo')))[0]
            if len(lo) and len(hi) and k > 0 and s * (MC[k] - p15[hi[-1]]) > 0 and s * (MC[k - 1] - p15[hi[-1]]) <= 0:
                return k
        return None

    # -- conditions: each returns True / False (None = cannot tell -> treated as not met)
    def check(self, key, p, ev):
        cx = self.cx; s, te, L, A, price = ev['side'], ev['te'], ev['L'], ev['A'], ev['px']
        if key == 'h4dir':
            return self.h4dir(te) == s
        if key == 'prov':
            j = int(np.searchsorted(self.prvt, te, side='right')) - 1
            return j < 0 or (self.prv[j][1] == 'up') == (s > 0)
        if key in ('d1ma', 'd1ma_x'):
            ma = self.ma('D1', p.get('period', 75)); n = int(p.get('slope', 10)); j = int(np.searchsorted(cx.Td + DAY, te, side='right')) - 1
            if j < n or not np.isfinite(ma[j - n]):
                return None
            agree = s * (ma[j] - ma[j - n]) > 0 and s * (cx.cd[j] - ma[j]) > 0
            return agree if key == 'd1ma' else (not agree)
        if key == 'd1dow':
            Pdr = cx.Pdr; mk = Pdr[0] <= te; kk = Pdr[1][mk]; vv = Pdr[2][mk]; hh = vv[kk == 'hi'][-2:]; ll = vv[kk == 'lo'][-2:]; d = 0
            if len(hh) == 2 and len(ll) == 2:
                d = 1 if (hh[1] > hh[0] and ll[1] > ll[0]) else (-1 if (hh[1] < hh[0] and ll[1] < ll[0]) else 0)
            return d * s >= 0
        if key in ('h4ma',):
            ma = self.ma('H4', p.get('period', 20)); n = int(p.get('slope', 3)); j = int(np.searchsorted(self.C4, te, side='right')) - 1
            return j >= n and np.isfinite(ma[j - n]) and s * (ma[j] - ma[j - n]) > 0
        if key in ('h1ma', 'h1ma2'):
            ma = self.ma('H1', p.get('period', 75 if key == 'h1ma' else 20)); n = int(p.get('slope', 5 if key == 'h1ma' else 3))
            j = int(np.searchsorted(cx.C1, te, side='right')) - 1
            if j < n or not np.isfinite(ma[j - n]):
                return None
            ok = s * (ma[j] - ma[j - n]) > 0
            return ok and s * (cx.c1[j] - ma[j]) > 0 if key == 'h1ma' else ok
        if key == 'h1order':
            f, sl = self.ma('H1', p.get('fast', 20)), self.ma('H1', p.get('slow', 75)); j = int(np.searchsorted(cx.C1, te, side='right')) - 1
            return bool(np.isfinite(f[j]) and np.isfinite(sl[j]) and s * (f[j] - sl[j]) > 0)
        if key == 'touch':
            P4 = self.P4; m = (P4[0] <= te) & (P4[0] >= te - float(p.get('days', 90)) * DAY) & (np.abs(P4[2] - L) <= float(p.get('width', 0.25)) * A)
            return int(m.sum()) >= int(p.get('n', 2))
        if key == 'uscore':     # the trader's own entry score (D18): line +1, impulse TL +2, H1 MA +1, correction TL +1, M15 TL +1
            pts = float(p.get('line', 1))
            pts += float(p.get('imp', 2)) * bool(self.check('impany', {}, ev)) + float(p.get('ma', 1)) * bool(self.check('h1ma', {'period': 75, 'slope': 5}, ev))
            pts += float(p.get('ctr', 1)) * bool(self.check('ctr41', {}, ev)) + float(p.get('m15', 1)) * bool(self.check('ctr15', {}, ev))
            ev['_uscore'] = pts
            return pts >= float(p.get('n', 4))
        if key == 'impany':
            a, b = self.check('imp4', {}, ev), self.check('impd', {}, ev)
            return None if (a is None and b is None) else bool(a or b)
        if key == 'ctr41':
            a, b = self.check('ctr1', {}, ev), self.check('ctr4', {}, ev)
            return None if (a is None and b is None) else bool(a or b)
        if key in ('imp4', 'impd', 'noimpbrk', 'score'):
            sc = ev.get('_score')
            if sc is None:
                try:
                    k1 = int(np.searchsorted(cx.C1, te, side='right')) - 1
                    ma = bool(s * (cx.s20[k1] - cx.s75[k1]) > 0) or bool(s * (cx.s75[k1] - cx.s75[k1 - 5]) > 0)
                    st0 = L - s * 0.3 * A; risk = s * (price - st0)
                    sc = dsc._score(cx, dict(side=s, t=pd.Timestamp(te), entry=price, st0=st0, risk_atr=max(risk, 1e-9) / A, lvl_born=pd.Timestamp(ev['born']),
                                             ma=ma, m15line=bool(self.check('ctr15', {}, ev)), risk_ahead=False))
                except Exception:
                    sc = {}
                ev['_score'] = sc
            if not sc:
                return None
            if key == 'imp4':
                return bool(sc.get('imp4'))
            if key == 'impd':
                return bool(sc.get('impd'))
            if key == 'noimpbrk':
                return not sc.get('impbrk')
            return sc.get('score', -9) >= int(p.get('n', 2))
        if key == 'noopp':
            S4 = cx.S['H4']; ts = S4(te); so = -s; C4s, c4s = cx.CS['H4']
            Ls = dsc._imp_lines(cx.PP['H4'], 'lo' if so > 0 else 'hi', so, ts, ts - S4(te - 60 * DAY), C4s, c4s, A, 0.3, 0.2, cx.H4h, cx.H4l, S4(cx.T4), 1.0)
            return not any(not y['broken'] for y in Ls)
        if key in ('ctr4', 'ctr1', 'ctr15'):
            tf = {'ctr4': 'H4', 'ctr1': 'H1', 'ctr15': 'M15'}[key]; kind = 'hi' if s > 0 else 'lo'
            k4 = int(np.searchsorted(cx.T4, np.datetime64(ev['born']))); k = int(np.searchsorted(self.C4, te, side='right')) - 1
            if k4 >= k or k4 < 0:
                k4 = max(0, k - 60)
            seg = (cx.H4h if s > 0 else cx.H4l)[k4:k + 1]
            if not len(seg):
                return None
            cst = cx.T4[k4 + int(np.argmax(seg) if s > 0 else np.argmin(seg))]
            P = cx.PP[tf]; CT, Cc = cx.CS[tf]; ts = cx.S[tf](te)
            t0 = cx.S[tf](max(cst, te - 2 * DAY)) if tf == 'M15' else cx.S[tf](cst - 4 * HOUR)
            cl = [x for x in dsc._lines(P, kind, s, t0, ts, CT, Cc, A) if s * (P[2][x[1]] - P[2][x[0]]) < 0]; b = dsc._steepest(cl, s)
            if not b:
                return None
            v = P[2][b[0]] + b[2] * ((ts - P[3][b[0]]) / HOUR)
            return s * (price - v) > 0
        if key == 'run':
            n = int(p.get('bars', 24)); j = int(np.searchsorted(cx.C1, te, side='right')) - 1
            if j < n:
                return None
            return abs(cx.c1[j] - cx.c1[j - n]) / max(cx.a1[j], 1e-12) < float(p.get('atr', 3.0))
        if key == 'madist':
            ma = self.ma('H4', p.get('period', 75)); j = int(np.searchsorted(self.C4, te, side='right')) - 1
            return bool(np.isfinite(ma[j]) and abs(price - ma[j]) / A <= float(p.get('atr', 2.0)))
        if key == 'depth':
            P4 = self.P4; m = P4[0] <= te; kk, vv = P4[1][m], P4[2][m]
            hi = vv[kk == ('hi' if s > 0 else 'lo')]; lo = vv[kk == ('lo' if s > 0 else 'hi')]
            if not len(hi) or not len(lo):
                return None
            top, base = hi[-1], lo[-1]; leg = s * (top - base)
            if leg <= 0:
                return None
            d = s * (top - price) / leg
            return float(p.get('min', 0)) <= d <= float(p.get('max', 1))
        if key == 'days':
            j = int(np.searchsorted(self.pvt, te, side='right')) - 1
            if j < 0:
                return None
            d = (te - self.pvt[j]) / DAY
            return float(p.get('min', 0)) <= d <= float(p.get('max', 9999))
        if key == 'hours':
            h = pd.Timestamp(te).tz_localize('Europe/Athens', ambiguous=True, nonexistent='shift_forward').tz_convert('Asia/Tokyo').hour
            a, b = int(p.get('from', 0)), int(p.get('to', 24)); hh = h if h >= a else h + 24
            return a <= hh < max(b, a + 1)
        return None


def ea_lines(sym, m, life=30, scenes=('gateway', 'fortress', 'band')):
    """2026-11-22 (report's all-pairs charts): the H4 lines the EA / alerts use that are still alive at the last bar.
    gateway / fortress: born within `life` days and no H4 close through the line since (side-wise); band: born within `life` days.
    -> [dict(kind, side, price (real price), born (server time, the H4 close that made the line))]"""
    mk = Market(sym, m); k = 100.0 if sym.endswith('JPY') else 1.0
    end = mk.C4[-1] if len(mk.C4) else None; out, seen = [], set()
    if end is None:
        return out
    c4 = np.asarray(mk.cx.c4, float); C4 = np.asarray(mk.C4, dtype='datetime64[ns]')
    for kind, side, L, born, _ in mk.lines(list(scenes), life):
        born = np.datetime64(born, 'ns')
        if (np.datetime64(end, 'ns') - born) > np.timedelta64(int(life), 'D'):
            continue
        if kind == 'band':
            key = ('band', round(L, 6))
            if key in seen:
                continue
            seen.add(key); side = 0
        else:
            after = c4[C4 > born]
            if len(after) and (side * (after - L) < 0).any():
                continue
        out.append(dict(kind=kind, side=int(side), price=float(L) * k, born=pd.Timestamp(born)))
    return out


LIFE_BARS, BAND_WIN, BAND_TOL = 180, 540, 0.25      # the H4 rules in bars (30 days / 90 days of H4), used on every timeframe


def tf_levels(df, R, k, tf):
    """2026-11-22 (user, chart analysis): the same horizontal lines on every timeframe, from that timeframe's major Dow.
      gateway  (出入口): the protected level broken at a turn, born within LIFE_BARS, no close through it since
      fortress (砦)   : the current protected level
      band     (抵抗体): >= 2 swings within BAND_TOL ATR over BAND_WIN bars, born within LIFE_BARS; and older protected levels
                        still alive (born within LIFE_BARS, no close through)
    -> [dict(type 'h', kind, tf, side, t1, p1)] in real prices (k = price-space factor)"""
    from env_recognition.pivots import atr
    from mt5_ea.live.eas import tlines
    T = pd.to_datetime(df.t).reset_index(drop=True); C = df.c.to_numpy(float); n = len(df); A = np.asarray(atr(df), float); out = []
    alive = lambda i, L, s: (n - 1 - i) <= LIFE_BARS and not (s * (C[i + 1:] - L) < 0).any()
    tr, prot = (R['bars'][-1] if R['bars'] else (None, None)); cur = None
    if tr in ('up', 'down') and prot is not None:
        anc = [e.get('prot_anchor') for e in R['all_events'] if e.get('machine') == 'major' and e.get('prot_price') is not None and abs(float(e['prot_price']) - float(prot)) < 1e-12]
        ia = int(anc[-1]) if anc and anc[-1] is not None else n - 1
        cur = float(prot); out.append(dict(type='h', kind='fortress', tf=tf, side=1 if tr == 'up' else -1, t1=T[min(ia, n - 1)], p1=cur * k))
    seen = set() if cur is None else {round(cur, 6)}
    for e in R['all_events']:
        if e.get('machine') != 'major':
            continue
        i = int(e['idx'])
        if e['action'] == 'REVERSAL' and e.get('broken_price') is not None:
            L, s = float(e['broken_price']), (1 if e['to'] == 'up' else -1)
            a0 = e.get('broken_anchor')                    # the line starts at the swing that was broken (the 出入口 itself)
            if alive(i, L, s) and round(L, 6) not in seen:
                seen.add(round(L, 6)); out.append(dict(type='h', kind='gateway', tf=tf, side=s, t1=T[min(int(a0) if a0 is not None else i, n - 1)], p1=L * k))
        elif e.get('action') == 'breakout_protect' and e.get('prot_price') is not None:
            L, s = float(e['prot_price']), (1 if e['trend'] == 'up' else -1)
            a0 = e.get('prot_anchor')
            if alive(i, L, s) and round(L, 6) not in seen:
                seen.add(round(L, 6)); out.append(dict(type='h', kind='band', tf=tf, side=0, t1=T[min(int(a0) if a0 is not None else i, n - 1)], p1=L * k))
    piv = sorted(tlines.pivots(R), key=lambda p: p[3]); have = []
    for ii, (i, kind, p, av) in enumerate(piv):
        if av >= n or not np.isfinite(A[av]):
            continue
        prev = [q for q in piv[:ii] if av - q[3] <= BAND_WIN and abs(q[2] - p) <= BAND_TOL * A[av]]
        if not prev:
            continue
        L = float(np.mean([q[2] for q in prev] + [p]))
        if any(abs(L - x) <= BAND_TOL * A[av] for x, _ in have):
            continue
        have.append((L, av))
        if (n - 1 - av) <= LIFE_BARS and round(L, 6) not in seen and all(abs(L * k - o['p1']) > BAND_TOL * A[av] * k for o in out):
            out.append(dict(type='h', kind='band', tf=tf, side=0, t1=T[av], p1=L * k))
    return out


def ea_chart_objects(sym, m, life=30):
    """2026-11-22 (report's chart analysis): what the EAs would watch now, for one pair, on D1 / H4 / H1 / M15 alike:
      horizontal lines from tf_levels() (出入口 / 砦 / 抵抗体) and trendlines (D1 / H4 / H1 open lines of tlines.build, the DL / HL
      rules; M15 = the C EA's unbroken correction lines)
    -> [dict(type 'h' | 't', kind, tf, side, t1, p1, t2, p2)] in real prices; t = bar open time (server time)"""
    from mt5_ea.live.eas import tlines, c as C15
    from env_recognition import dow_trend
    from env_recognition.pivots import atr
    mk = Market(sym, m); F = mk.F; k = 100.0 if sym.endswith('JPY') else 1.0; out = []
    D = F.m15_all.set_index('t').resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    frames = {'D1': (D, dow_trend.run(D[['t', 'o', 'h', 'l', 'c']], 'D1')), 'H4': (F.h4.reset_index(drop=True), F.R4),
              'H1': (F.h1.reset_index(drop=True), F.R1), 'M15': (F.m15.reset_index(drop=True), F.R15)}
    for tf, (df, R) in frames.items():
        T = pd.to_datetime(df.t).reset_index(drop=True)
        out += tf_levels(df, R, k, tf)
        if tf in ('D1', 'H4', 'H1', 'M15'):              # every line still open on every timeframe (2026-11-22, user)
            A = np.asarray(atr(df), float)
            for ln in tlines.build(df, R, A, tf, early=True, h4c=None, maxspan=60 if tf == 'D1' else None):
                if ln['why'] != 'open':
                    continue
                (ia, pa), (ib, pb) = ln['anchor'], ln['pts'][-1]
                if ib >= len(T) or ia >= len(T):
                    continue
                out.append(dict(type='t', kind='tl', tf=tf, side=int(ln['side']), t1=T[ia], p1=float(pa) * k, t2=T[ib], p2=float(pb) * k))
    LS, _ = C15.lines(F); T15 = pd.to_datetime(F.m15.t).reset_index(drop=True)
    for ia, pa, ib, pb, cr, en, kind, broken in LS:
        if en is None and not broken and ib < len(T15):
            out.append(dict(type='t', kind='cl15', tf='M15', side=-1 if kind == 'hi' else 1, t1=T15[ia], p1=float(pa) * k, t2=T15[ib], p2=float(pb) * k))
    for o in out:
        o.setdefault('t2', None); o.setdefault('p2', None)
    return out


def events(mk, prof, since):
    """moments where price came back to one of the profile's lines (timing near / turn) at or after `since`"""
    out = []; t_from = np.datetime64(pd.Timestamp(since)) if since is not None else np.datetime64(pd.Timestamp(mk.start))
    near, away, life = float(prof.get('near', 0.3)), float(prof.get('away', 1.0)), float(prof.get('life', 30))
    for scene, s, L, born, lf in mk.lines(set(prof.get('scenes') or []), life):
        if born + int(lf) * DAY < t_from - 2 * DAY:
            continue
        tms_all = prof.get('timings') or [prof.get('timing') or 'turn']
        if 'tl15' in tms_all or 'zone' in tms_all:   # 2026-11-22/23: in the ⭐ zone, on the M15 trendline break (zone: or the M15 Dow turn)
            out += zone_breaks(mk, prof, scene, s, L, born, lf, t_from, turn='zone' in tms_all)
        tms = [t for t in tms_all if t in ('turn', 'stm15', 'sth1')]
        if not tms:
            continue
        tch, A = mk.touches(L, s, born, lf, near, away, float(prof.get('brk', 0.0)))
        for q, n in tch:                        # every return to the line (2026-11-21)
            if mk.CL[q] + 2 * DAY < t_from:
                continue
            for tm in tms:                      # 2026-11-21 (user): every chosen signal sends its own alert (once per touch and signal)
                if tm in ('stm15', 'sth1'):
                    hit = mk.stoch_after(q, L, s, A, 'M15' if tm == 'stm15' else 'H1')
                else:                           # 'turn' (old settings saved as 'near' also come here: no alert on the touch itself)
                    qt = mk.turn_after(q, L, s, A); hit = None if qt is None else (mk.CL[qt], float(mk.MC[qt]))
                if hit is None or hit[0] < t_from:
                    continue
                out.append(dict(scene=scene, side=s, L=L, A=A, born=born, te=hit[0], px=hit[1], tm=tm, n=n, tq=mk.CL[q]))
    return out


REARM = np.timedelta64(12, 'h')     # in the same approach, another alert only 12 hours after the last one (and on a new signal)


def zone_breaks(mk, prof, scene, s, L, born, lf, t_from, turn=False):
    """2026-11-22 (user: his entries were 1-2.6 ATR(H4) before the H4 line, on the M15 trendline break, and the touch-based alert never
    came). Timing 'tl15': price broke out and left the line by `away` ATR(H4), came back within `zone` ATR(H4) of it (the ⭐ zone), and an
    M15 correction trendline (the one the score's M15TL point uses) breaks toward the trade -> one alert per approach (a new approach
    starts after price leaves the zone again). Ends when an H4 close goes through the line or the line's life is over."""
    away, zone, brk = float(prof.get('away', 1.0)), float(prof.get('zone', 2.5)), float(prof.get('brk', 0.0))
    A = mk.a4(born); TM, MC, CL = mk.TM, mk.MC, mk.CL
    q0 = int(np.searchsorted(TM, born)); q1 = min(int(np.searchsorted(TM, born + int(lf) * DAY)), len(TM))
    k0 = int(np.searchsorted(mk.C4, born, side='right')); k1 = int(np.searchsorted(mk.C4, born + int(lf) * DAY))
    thr = np.nonzero(s * (np.asarray(mk.cx.c4[k0:k1], float) - L) < -brk * A)[0]
    if len(thr):
        q1 = min(q1, int(np.searchsorted(TM, mk.C4[k0 + thr[0]])))
    if q1 <= q0:
        return []
    d = s * (MC[q0:q1] - L) / A
    if scene == 'fortress' and float(prof.get('band', 1)):
        e = fortress_edge(mk, s, L, born)
        if e is not None:
            d = np.where(d < 0, d, np.maximum(s * (MC[q0:q1] - e) / A, 0.0))
    left = np.maximum.accumulate(d >= away)
    out, last_fire, prev, qz, tq = [], None, None, None, None      # 2026-11-23 (user): once more after 12 h if the signal comes again
    c15, k15, p15, t15 = mk.P15
    for j in range(len(d)):
        q = q0 + j
        inz = bool(left[j]) and -0.4 <= d[j] <= zone
        if not inz:
            if d[j] > zone:
                last_fire = None                 # left the zone: the next approach may alert again at once
            prev = None; qz = None; continue
        if qz is None:
            qz = q                               # this approach entered the zone here
        if (last_fire is not None and CL[q] < last_fire + REARM) or CL[q] + 2 * DAY < t_from:
            prev = None if last_fire is not None and CL[q] < last_fire + REARM else prev
            continue
        ev = dict(scene=scene, side=s, L=L, A=A, born=born, te=CL[q], px=float(MC[q]))
        cur = bool(mk.check('ctr15', {}, ev))
        hit = 'tl15' if (cur and prev is False) else None
        if not hit and turn and q > qz:          # the M15 Dow turn toward the trade: close beyond the last M15 swing against it
            m = (c15 <= CL[q]); hi = np.nonzero(m & (k15 == ('hi' if s > 0 else 'lo')) & (t15 >= TM[qz] - 2 * HOUR))[0]
            if len(hi) and s * (MC[q] - p15[hi[-1]]) > 0 and s * (MC[q - 1] - p15[hi[-1]]) <= 0:
                hit = 'turn'
        if hit and CL[q] >= t_from:
            out.append(dict(scene=scene, side=s, L=L, A=A, born=born, te=CL[q], px=float(MC[q]), tm=hit if not turn else 'zone_' + hit, n=1, tq=CL[q]))
            last_fire = CL[q]; qz = q            # the next one needs a new break / a new turn from here
        prev = cur
    return out


def star_why(mk, profiles, at, side, star=None):
    """why the ⭐ is not on for `side` at bar `at` (the mark's answer check): the reason of the nearest line of that side"""
    st = dict(STAR_DEFAULT); st.update({k: v for k, v in (star or {}).items() if k in STAR_DEFAULT}); zone = float(st['zone'])
    now = mk.CL[at]; best = None
    for prof in profiles:
        if not prof.get('on') or (prof.get('pairs') and mk.sym not in prof['pairs']):
            continue
        away, life = float(prof.get('away', 1.0)), float(prof.get('life', 30))
        for scene, sd, L, born, lf in mk.lines(set(prof.get('scenes') or []), life):
            if sd != side or born > now or born + int(lf) * DAY < now:
                continue
            A = mk.a4(born)
            k0 = int(np.searchsorted(mk.C4, born, side='right')); k1 = int(np.searchsorted(mk.C4, now, side='right'))
            if (sd * (np.asarray(mk.cx.c4[k0:k1], float) - L) < 0).any():
                continue
            q0 = int(np.searchsorted(mk.TM, born)); d = sd * (mk.MC[q0:at + 1] - L) / A
            if scene == 'fortress' and float(st.get('band', 1)):
                e = fortress_edge(mk, sd, L, born)
                if e is not None:
                    d = np.where(d < 0, d, np.maximum(sd * (mk.MC[q0:at + 1] - e) / A, 0.0))
            if not len(d):
                continue
            if not (d >= away).any():
                why = f'線から一度も {away:g}ATR 離れていない'
            elif d[-1] > zone:
                why = f'線から遠い（終値で {d[-1]:.1f}ATR、⭐ は {zone:g} まで）'
            else:
                ev = dict(scene=scene, side=sd, L=L, A=A, born=born, te=now, px=float(mk.MC[at]), tm='turn', n=1, tq=now)
                bad = [CATALOG[k][0] for k, par in (prof.get('conds') or {}).items() if k in CATALOG and k != 'uscore' and not mk.check(k, dict(CATALOG[k][1], **(par or {})), ev)]
                if bad:
                    why = '条件：' + '・'.join(bad)
                elif float(st['n']) > 0 and not mk.check('uscore', {k: float(st[k]) for k in ('n', 'line', 'imp', 'ma', 'ctr', 'm15')}, ev):
                    why = f"点数が足りない（{ev.get('_uscore', 0):g} 点、⭐ は {float(st['n']):g} 点から）"
                else:
                    why = 'M15 の転換がもう出ていた（その後は ⭐ を消す）'
            dist = abs(d[-1])
            if best is None or dist < best[0]:
                best = (dist, f"{SCENE_JA[scene]}：{why}")
    return best[1] if best else 'その向きの H4 の砦・出入口がない'


def evaluate(mk, profiles, since=None):
    res = []
    for prof in profiles:
        if not prof.get('on'):
            continue
        if prof.get('pairs') and mk.sym not in prof['pairs']:
            continue
        for ev in events(mk, prof, since):
            ok, met = True, []
            for key, par in (prof.get('conds') or {}).items():
                if key not in CATALOG:
                    continue
                p = dict(CATALOG[key][1]); p.update(par or {})
                r = mk.check(key, p, ev)
                if not r:
                    ok = False; break
                met.append(CATALOG[key][0])
            if not ok:
                continue
            d1 = mk.check('d1ma', {'period': 75, 'slope': 10}, ev)
            meth = ('1' if d1 else '6') if ev['scene'] == 'gateway' else (('2' if d1 else '7') if ev['scene'] == 'fortress' else '')
            k = mk.k
            res.append(dict(sym=mk.sym, profile=prof.get('id', ''), pname=prof.get('name', ''), kind=SCENE_JA[ev['scene']], side=ev['side'], method=meth,
                            timing=ev.get('tm', 'turn'), n=ev.get('n', 1), touch_t=pd.Timestamp(ev.get('tq', ev['te'])), t=pd.Timestamp(ev['te']), line=round(ev['L'] * k, 6), atr=round(ev['A'] * k, 6),
                            price=round(ev['px'] * k, 6), born=pd.Timestamp(ev['born']), d1=int(bool(d1)), h1=int(bool(mk.check('h1ma', {'period': 75, 'slope': 5}, ev))),
                            touch=int(((mk.P4[0] <= ev['te']) & (mk.P4[0] >= ev['te'] - 90 * DAY) & (np.abs(mk.P4[2] - ev['L']) <= 0.25 * ev['A'])).sum()),
                            met=met, uscore=ev.get('_uscore')))
    # 2026-11-23: two 砦 next to each other gave the same alert twice at the same bar -> one per pair, side and bar
    seen, out = set(), []
    for a in res:
        k = (a['side'], str(a['t']), a['timing'])
        if k not in seen:
            seen.add(k); out.append(a)
    return out


STAR_DEFAULT = {'zone': float(os.getenv('EA_STAR_ATR') or 2.5), 'n': 3, 'line': 1, 'imp': 2, 'ma': 1, 'ctr': 1, 'm15': 0, 'band': 1}   # = ea_live.js STAR_DEFAULT; band: 砦 as an area


def fortress_edge(mk, s, L, born):
    """2026-11-23 (user): a 砦 is an area, not a line: from the H4 swing that made it down to the M15 押し安値 (for a buy: up to the
    M15 戻り高値) of the day it was made, where buyers and sellers piled up and price often turns again. = the lowest M15 low (sell)
    in the 24 hours before the H4 swing bar and that bar itself, within 1.5 ATR(H4) of the line. None when there is none."""
    ct, kd, pp, bt = mk.P4; kind = 'hi' if s < 0 else 'lo'
    m = np.nonzero((kd == kind) & np.isclose(pp, L, rtol=0, atol=1e-9) & (ct <= np.datetime64(born)))[0]
    if not len(m):
        return None
    tb = bt[m[-1]]; A = mk.a4(born)
    c15, k15, p15, b15 = mk.P15
    w = (k15 == ('lo' if s < 0 else 'hi')) & (b15 >= tb - 24 * HOUR) & (b15 < tb + 4 * HOUR)
    v = p15[w]; v = v[(s * (v - L) >= 0) & (np.abs(v - L) <= 1.5 * A)]          # below the 砦 for a sell, above it for a buy
    if not len(v):
        return None
    return float(v.min() if s < 0 else v.max())


def armed(mk, profiles, zone=None, at=None, star=None):
    """2026-11-22 (user): 「もうすぐ」 for the pair tab, about a day BEFORE the entry. A line of a profile that is on (H4 出入口 / 砦,
    still alive: no H4 close through it, within its life), price has broken out and left it by `away` ATR(H4) at least once, and is now
    within `zone` ATR(H4) of it on the trade side (2.5: in the past alerts of EURUSD / EURJPY price was 1.65 ATR away 24 h before the
    alert on the median; with 2.5 the star came a median 24 h ahead, 16 h for the first quarter). Gone when price runs further than
    `zone` (trend went on), when an H4 close goes through the line, or once the M15 turn came after a touch (the entry / the alert).
    The profile's conditions are checked now, the score without the M15 TL point (4 -> 3 with the presets).
    -> [{sym, side, method, kind, line, dist, text}], one per line."""
    st = dict(STAR_DEFAULT); st.update({k: v for k, v in (star or {}).items() if k in STAR_DEFAULT})   # the app's ⭐ settings
    zone = float(st['zone']) if zone is None else zone
    out, seen = [], set(); last = len(mk.TM) - 1 if at is None else int(at)      # at: an earlier bar (checks on history)
    if last < 1:
        return out
    now, k = mk.CL[last], mk.k
    for prof in profiles:
        if not prof.get('on') or (prof.get('pairs') and mk.sym not in prof['pairs']):
            continue
        near, away, life, brk = float(prof.get('near', 0.3)), float(prof.get('away', 1.0)), float(prof.get('life', 30)), float(prof.get('brk', 0.0))
        for scene, sd, L, born, lf in mk.lines(set(prof.get('scenes') or []), life):
            if born + int(lf) * DAY < now or born > now:
                continue
            A = mk.a4(born)
            k0 = int(np.searchsorted(mk.C4, born, side='right')); k1 = int(np.searchsorted(mk.C4, now, side='right'))
            if (sd * (np.asarray(mk.cx.c4[k0:k1], float) - L) < -brk * A).any():      # an H4 close went through the line: gone
                continue
            q0 = int(np.searchsorted(mk.TM, born))
            d = sd * (mk.MC[q0:last + 1] - L) / A
            if scene == 'fortress' and float(st.get('band', 1)):                       # the 砦 as an area: distance to its near edge
                e = fortress_edge(mk, sd, L, born)
                if e is not None:
                    de = sd * (mk.MC[q0:last + 1] - e) / A
                    d = np.where(d < 0, d, np.maximum(de, 0.0))
            if not len(d) or not (d >= away).any() or d[-1] > zone:                    # never left yet / too far now
                continue
            out_ = np.nonzero(d > zone)[0]
            z = q0 + (int(out_[-1]) + 1 if len(out_) else int(np.argmax(d >= away)))     # where this approach began
            tch, _ = mk.touches(L, sd, born, lf, near, away, brk)
            if any(z <= q <= last and mk.turn_after(q, L, sd, A, n=last - q + 1, stop=None) is not None for q, _n in tch):
                continue                                                               # turned already (entry / alert)
            ev = dict(scene=scene, side=sd, L=L, A=A, born=born, te=now, px=float(mk.MC[last]), tm='turn', n=1, tq=now)
            ok = True
            for key, par in (prof.get('conds') or {}).items():
                if key in CATALOG and key != 'uscore':     # the score: the ⭐'s own points and total below
                    p = dict(CATALOG[key][1]); p.update(par or {})
                    if not mk.check(key, p, ev):
                        ok = False; break
            if ok and float(st['n']) > 0:
                ok = bool(mk.check('uscore', {k: float(st[k]) for k in ('n', 'line', 'imp', 'ma', 'ctr', 'm15')}, ev))
            if not ok:
                continue
            line = round(L * k, 5 if k == 1.0 else 3)
            if (sd, scene, line) in seen:
                continue
            seen.add((sd, scene, line))
            d1 = mk.check('d1ma', {'period': 75, 'slope': 10}, ev)
            meth = ('1' if d1 else '6') if scene == 'gateway' else (('2' if d1 else '7') if scene == 'fortress' else '')
            dist = round(float(max(d[-1], 0.0)), 1)
            out.append(dict(sym=mk.sym, side=sd, method=meth, kind=SCENE_JA[scene], line=line, dist=dist,
                            text=f"{'↑' if sd > 0 else '↓'} {('手法' + meth + ' ') if meth else ''}H4{SCENE_JA[scene]} {line}（{dist}ATR 乖離）"))
    return out


def classify_point(sym, m15, te, side, price):
    """2026-11-22 (user): a mark the trader put on the report's chart (エントリーしたかった所) sorted afterwards, the way the alerts see it:
    the nearest live H4 出入口 / 砦 of that side at that moment (as known then: bars up to the mark only), its distance in ATR(H4),
    D1 〇 / ✕, so 手法 1 / 2 / 6 / 7, and the score items (推進TL 2, 調整TL 1, H1 MA 1, M15 TL 1, line 1).
    side +1 buy / -1 sell, te broker time, price in the broker's price."""
    m = m15[pd.to_datetime(m15.t) <= pd.Timestamp(te)].tail(DAYS * 96).reset_index(drop=True)
    mk = Market(sym, m); last = len(mk.TM) - 1
    if last < 200:
        return None
    now, k = mk.CL[last], mk.k; px = float(price) / k
    best = None
    for scene, sd, L, born, lf in mk.lines({'gateway', 'fortress'}, 30):
        if sd != side or born > now or born + int(lf) * DAY < now:
            continue
        A = mk.a4(born)
        k0 = int(np.searchsorted(mk.C4, born, side='right')); k1 = int(np.searchsorted(mk.C4, now, side='right'))
        if (sd * (np.asarray(mk.cx.c4[k0:k1], float) - L) < 0).any():
            continue
        d = sd * (px - L) / A
        if d < -0.5:
            continue
        if best is None or abs(d) < abs(best[4]):
            best = (scene, L, A, born, d)
    A = best[2] if best else mk.a4(now)
    ev = dict(scene=best[0] if best else '', side=side, L=best[1] if best else px, A=A, born=best[3] if best else now, te=now, px=px, tm='turn', n=1, tq=now)
    chk = lambda key, par=None: bool(mk.check(key, par or {}, ev))
    d1 = chk('d1ma', {'period': 75, 'slope': 10})
    near = best is not None and best[4] <= 3.0
    meth = (('1' if d1 else '6') if best[0] == 'gateway' else ('2' if d1 else '7')) if near else ''
    it = dict(imp=chk('impany'), ma=chk('h1ma', {'period': 75, 'slope': 5}), ctr=chk('ctr41'), m15=chk('ctr15'))
    return dict(method=meth, kind=SCENE_JA[best[0]] if near else '', line=round(best[1] * k, 5 if k == 1.0 else 3) if near else None,
                dist=round(float(best[4]), 2) if near else None, d1=d1, h4dir=chk('h4dir'), **it,
                score=(1 if near else 0) + 2 * it['imp'] + it['ma'] + it['ctr'] + it['m15'])


def scan(sym, m, since=None, profiles=None):
    return evaluate(Market(sym, m), profiles or PRESETS[:1], since)


def jst(t):
    return pd.Timestamp(t).tz_localize('Europe/Athens', ambiguous=True, nonexistent='shift_forward').tz_convert('Asia/Tokyo').strftime('%Y-%m-%d %H:%M')


def text(a):
    dj = '買い' if a['side'] > 0 else '売り'; o = lambda v: '〇' if v else '✕'
    how = {'near': '線に近づいた', 'turn': '線で反発して M15 がダウ転換', 'zone_tl15': '⭐ の範囲で M15 のトレンドライン抜け', 'zone_turn': '⭐ の範囲で M15 がダウ転換',
           'tl15': '⭐ の範囲で M15 のトレンドライン抜け', 'stm15': '線で反発して M15 ストキャス', 'sth1': '線で反発して H1 ストキャス'}.get(a['timing'], '')
    lines = [f"🔔 {a['pname']}", f"{a['sym']} {dj}：{a['kind']} {a.get('n', 1)} 回目の戻り（{how}）{('・手法' + a['method']) if a['method'] else ''}",
             f"線 {a['line']:g}・今 {a['price']:g}（{abs(a['price'] - a['line']) / a['atr']:.1f}ATR）",
             f"日足 {o(a['d1'])}・H1 MA75 {o(a['h1'])}・線の山谷 {a['touch']} 個", f"足 {a['jst']}（日本時間）"]
    if a.get('uscore') is not None:
        lines.append(f"点数 {a['uscore']:g} 点")
    if a.get('met'):
        lines.append('条件：' + ' / '.join(a['met'][:8]))
    return '\n'.join(lines)


def settings_from(r, cur):
    s = (r or {}).get('settings') if isinstance(r, dict) else None
    if not isinstance(s, dict):
        return cur
    out = dict(cur); out['on'] = s.get('on', True)
    if s.get('v') == ALERTS_V and isinstance(s.get('profiles'), list) and s['profiles']:   # older saved sets -> the presets
        out['profiles'] = s['profiles']
    if isinstance(s.get('star'), dict):                       # 2026-11-22: the ⭐ settings from the app
        out['star'] = s['star']
    return out


def _single_instance(path):
    """Hold an OS lock on `path` for the life of the process; False when another copy holds it."""
    f = open(path, 'a+')
    try:
        if os.name == 'nt':
            import msvcrt
            f.seek(0); msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close(); return None
    return f


def main():
    from mt5_ea.live import gas
    from mt5_ea.live.broker import MT5Broker
    from mt5_ea import telegram_notify as tg
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    data = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data'); data.mkdir(exist_ok=True)
    lock = _single_instance(data / 'alerts.lock')
    if lock is None:
        print('裁量の通知はもう別の窓で動いています。この窓は閉じます。', flush=True)
        return 3
    stf = data / 'alerts_state.json'
    st = json.loads(stf.read_text(encoding='utf-8')) if stf.exists() else {'sent': [], 'last_bar': ''}
    path = os.getenv('EA_ALERT_MT5_PATH') or os.getenv('EA_DEMO_MT5_PATH') or ''
    if path:
        os.environ['EA_MT5_PATH'] = path
    b = MT5Broker()
    cfg = {'on': True, 'profiles': PRESETS}
    try:
        cfg = settings_from(gas.call('eaAlert', {'alerts': []}, timeout=60), cfg)
    except Exception as ex:
        logging.warning('GAS: %s', ex)
    print('裁量の通知を始めました（注文はしません）。この窓を閉じると止まります。', flush=True)
    first = True
    while True:
        try:
            last = b.bars('EURUSD', 2).t.iat[-1]
            if str(last) != st['last_bar']:
                since = pd.Timestamp(last) - (pd.Timedelta(minutes=15) if first else pd.Timedelta(hours=1))
                profs = [p for p in cfg.get('profiles') or [] if p.get('on')] if cfg.get('on', True) else []
                new, arm = [], []
                if profs:
                    for sym in PAIRS:
                        try:
                            mk = Market(sym, b.bars(sym, DAYS))
                            try:
                                arm += armed(mk, profs, star=cfg.get('star'))          # 2026-11-22: 「もうすぐエントリー」 for the pair tab
                            except Exception as ex:
                                logging.warning('%s armed: %s', sym, ex)
                            for a in evaluate(mk, profs, since):
                                aid = f"{a['profile']}|{a['timing']}|{a['sym']}|{a['kind']}|{a['side']}|{a['line']}|{a['born']}|{a['touch_t']}"
                                if aid in st['sent']:
                                    continue
                                a['jst'] = jst(a['t']); a['id'] = aid; new.append(a)
                        except Exception as ex:
                            logging.warning('%s: %s', sym, ex)
                try:      # GAS: record the alerts, get the app's settings back
                    r = gas.call('eaAlert', {'alerts': [{k: (str(v) if isinstance(v, pd.Timestamp) else (' / '.join(v) if isinstance(v, list) else v)) for k, v in a.items()} for a in new],
                                             'armed': [{'sym': x['sym'], 'text': x['text']} for x in arm]}, timeout=60)
                    cfg = settings_from(r, cfg)
                except Exception as ex:
                    logging.warning('GAS: %s', ex)
                for a in new:
                    tg.send('alert', text(a), {'notifyAlert': True}); st['sent'].append(a['id'])
                st['sent'] = st['sent'][-5000:]; st['last_bar'] = str(last); first = False
                stf.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
                logging.info('bar %s: %d new alerts (%d profiles on)', last, len(new), len(profs))
                hour = str(pd.Timestamp(last).floor('h'))
                if os.getenv('EA_PAIR_ENV', '1') != '0' and hour != st.get('env_hour'):    # once an hour: trend arrows for the pair tab (400 days of M15 only, ~24 s; EA_PAIR_ENV=0 turns it off)
                    try:
                        from mt5_ea.live import pair_env
                        rows = pair_env.scan(b, pair_env.app_pairs(gas), timeout=60, weekly=False)   # W1: only PAIR_ENV.bat (weekend)
                        r = gas.call('eaPairEnv', {'pairs': rows}, timeout=90)
                        st['env_hour'] = hour; stf.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
                        logging.info('pair env: %d pairs sent, %s changed', len(rows), (r or {}).get('changed'))
                    except Exception as ex:
                        logging.warning('pair env: %s', ex)
                    if os.getenv('EA_TRADE_IMAGES', '1') != '0':      # 2026-11-22: chart images for imported trades (a few per hour)
                        try:
                            from mt5_ea.live import trade_images
                            n = trade_images.run(b, gas, limit=5, log=lambda x: logging.info(x))
                            if n:
                                logging.info('trade images: %d trades', n)
                        except Exception as ex:
                            logging.warning('trade images: %s', ex)
        except Exception as ex:
            logging.exception('alerts loop: %s', ex)
        try:
            auto_import(st, stf)
        except Exception as ex:
            logging.warning('auto import: %s', ex)
        time.sleep(20)



IMPORT_EVERY_MIN = float(os.getenv('EA_IMPORT_EVERY_MIN') or 60)


def auto_import(st, stf, now=None, start=None):
    """2026-11-22 (user): the MT5 import (the trader's own accounts) runs by itself once an hour while this window is open,
    weekends too (by the clock, not by new bars). Same as the desktop button (run_import.ps1: one import at a time, import.log);
    started in the background so the alerts go on. The button stays for an import right now. EA_AUTO_IMPORT=0 turns it off.
    Returns True when an import was started."""
    if os.getenv('EA_AUTO_IMPORT', '1') == '0':
        return False
    now = pd.Timestamp.now(tz='UTC') if now is None else pd.Timestamp(now)
    last = st.get('import_at')
    if last and now - pd.Timestamp(last) < pd.Timedelta(minutes=IMPORT_EVERY_MIN):
        return False
    st['import_at'] = str(now)
    stf.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
    ps1 = Path(__file__).resolve().parents[1] / 'run_import.ps1'
    if start is None:
        if os.name != 'nt' or not ps1.exists() or not (Path(os.getenv('EA_DATA_DIR') or (Path.home() / 'TradeEA_data')) / 'import_accounts.json').exists():
            return False
        import subprocess
        start = lambda: subprocess.Popen(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(ps1)],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                         creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    start()
    logging.info('auto import started (next in %.0f min)', IMPORT_EVERY_MIN)
    return True


if __name__ == '__main__':
    sys.exit(main())
