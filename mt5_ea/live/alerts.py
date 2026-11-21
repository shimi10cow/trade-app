"""Discretionary alerts (2026-11-21): 'そろそろ' notices for the trader's own setups, wider than the EAs. No orders, ever.

The trader keeps several alert profiles in the app (demo config 'alerts': {on, profiles: [...]}). A profile =
  scenes   gateway  (出入口, methods 1 / 6) = the last protected swing broken by an H4 major reversal
           fortress (砦,     methods 2 / 7) = the protected swing of the current H4 major trend (breakout_protect)
           band     (抵抗体)              = an H4 level where >= 2 H4 swings sit within 0.25 ATR (90 days), either side
  touch    the first M15 bar back within `near` ATR(H4) of the line after price had been >= `away` ATR beyond it
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
ALERTS_V = 2                  # 2026-11-21: settings version (2 = methods 1 / 2 / 6 / 7 presets); older saved profiles are replaced
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
    'noimpbrk': ('H4 の推進線を割っていない', {}),
    'noopp':   ('反対向きの H4 推進線が残っていない', {}),
    'ctr4':    ('H4 の逆トレンドライン（調整線）を抜けている', {}),
    'ctr1':    ('H1 の逆トレンドラインを抜けている', {}),
    'ctr15':   ('M15 の逆トレンドラインを抜けている', {}),
    'score':   ('D の点数（線の点数）が N 以上', {'n': 2}),
    'run':     ('直前に伸びすぎていない（H1 の n 本で x ATR 未満）', {'bars': 24, 'atr': 3.0}),
    'madist':  ('H4 の MA から離れすぎていない', {'period': 75, 'atr': 2.0}),
    'depth':   ('押しの深さ（直近の H4 の波に対して）', {'min': 0.1, 'max': 0.382}),
    'days':    ('H4 の本転換からの日数', {'min': 0, 'max': 30}),
    'hours':   ('時間帯（日本時間、何時から何時まで）', {'from': 8, 'to': 26}),
}

PRESETS = [   # 2026-11-21 (user): only the trader's own methods 1 / 2 / 6 / 7; the alert comes when entering (M15 Dow turn after the touch)
    dict(id='m1', name='手法1：日足〇・H4 出入口', on=True, scenes=['gateway'], timing='turn', near=0.3, away=1.0, life=30, pairs=[],
         conds={'h4dir': {}, 'd1ma': {'period': 75, 'slope': 10}}),
    dict(id='m2', name='手法2：日足〇・H4 砦', on=True, scenes=['fortress'], timing='turn', near=0.3, away=1.0, life=30, pairs=[],
         conds={'h4dir': {}, 'd1ma': {'period': 75, 'slope': 10}}),
    dict(id='m6', name='手法6：日足✕・H4 出入口', on=True, scenes=['gateway'], timing='turn', near=0.3, away=1.0, life=30, pairs=[],
         conds={'h4dir': {}, 'd1ma_x': {'period': 75, 'slope': 10}}),
    dict(id='m7', name='手法7：日足✕・H4 砦', on=True, scenes=['fortress'], timing='turn', near=0.3, away=1.0, life=30, pairs=[],
         conds={'h4dir': {}, 'd1ma_x': {'period': 75, 'slope': 10}}),
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

    def first_near(self, L, s, t0, life, near, away):
        TM, MC, MH, ML = self.TM, self.MC, self.MH, self.ML; A = self.a4(t0)
        q0 = int(np.searchsorted(TM, t0)); q1 = int(np.searchsorted(TM, t0 + int(life) * DAY))
        if q1 <= q0:
            return None, A
        far = np.nonzero(s * (MC[q0:q1] - L) >= away * A)[0]
        if not len(far):
            return None, A
        a = q0 + far[0]; hit = np.nonzero(s * ((ML if s > 0 else MH)[a:q1] - L) <= near * A)[0]
        if not len(hit):
            return None, A
        q = a + hit[0]
        return (None if len(np.nonzero(s * (MC[a:q + 1] - L) < -0.5 * A)[0]) else q), A

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

    def turn_after(self, q, L, s, A):
        """first M15 Dow turn toward the bounce within 12 hours of the touch (bar index), or None"""
        c15, k15, p15, t15 = self.P15; TM, MC, CL = self.TM, self.MC, self.CL
        for k in range(q, min(q + 48, len(TM))):
            if s * (MC[k] - L) < -0.4 * A:
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


def events(mk, prof, since):
    """moments where price came back to one of the profile's lines (timing near / turn) at or after `since`"""
    out = []; t_from = np.datetime64(pd.Timestamp(since)) if since is not None else np.datetime64(pd.Timestamp(mk.start))
    near, away, life = float(prof.get('near', 0.3)), float(prof.get('away', 1.0)), float(prof.get('life', 30))
    for scene, s, L, born, lf in mk.lines(set(prof.get('scenes') or []), life):
        if born + int(lf) * DAY < t_from - 2 * DAY:
            continue
        q, A = mk.first_near(L, s, born, lf, near, away)
        if q is None:
            continue
        tm = prof.get('timing') or 'turn'
        if tm in ('stm15', 'sth1'):
            hit = mk.stoch_after(q, L, s, A, 'M15' if tm == 'stm15' else 'H1')
            if hit is None:
                continue
            te, px = hit
        else:                                   # 'turn' (old settings saved as 'near' also come here: no alert on the touch itself)
            q = mk.turn_after(q, L, s, A)
            if q is None:
                continue
            te, px = mk.CL[q], float(mk.MC[q])
        if te < t_from:
            continue
        out.append(dict(scene=scene, side=s, L=L, A=A, born=born, te=te, px=px))
    return out


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
                            timing=prof.get('timing', 'turn'), t=pd.Timestamp(ev['te']), line=round(ev['L'] * k, 6), atr=round(ev['A'] * k, 6),
                            price=round(ev['px'] * k, 6), born=pd.Timestamp(ev['born']), d1=int(bool(d1)), h1=int(bool(mk.check('h1ma', {'period': 75, 'slope': 5}, ev))),
                            touch=int(((mk.P4[0] <= ev['te']) & (mk.P4[0] >= ev['te'] - 90 * DAY) & (np.abs(mk.P4[2] - ev['L']) <= 0.25 * ev['A'])).sum()),
                            met=met))
    return res


def scan(sym, m, since=None, profiles=None):
    return evaluate(Market(sym, m), profiles or PRESETS[:1], since)


def jst(t):
    return pd.Timestamp(t).tz_localize('Europe/Athens', ambiguous=True, nonexistent='shift_forward').tz_convert('Asia/Tokyo').strftime('%Y-%m-%d %H:%M')


def text(a):
    dj = '買い' if a['side'] > 0 else '売り'; o = lambda v: '〇' if v else '✕'
    how = {'near': '線に近づいた', 'turn': '線で反発して M15 がダウ転換', 'stm15': '線で反発して M15 ストキャス', 'sth1': '線で反発して H1 ストキャス'}.get(a['timing'], '')
    lines = [f"🔔 {a['pname']}", f"{a['sym']} {dj}：{a['kind']}（{how}）{('・手法' + a['method']) if a['method'] else ''}",
             f"線 {a['line']:g}・今 {a['price']:g}（{abs(a['price'] - a['line']) / a['atr']:.1f}ATR）",
             f"日足 {o(a['d1'])}・H1 MA75 {o(a['h1'])}・線の山谷 {a['touch']} 個", f"足 {a['jst']}（日本時間）"]
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
    return out


def main():
    from mt5_ea.live import gas
    from mt5_ea.live.broker import MT5Broker
    from mt5_ea import telegram_notify as tg
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    data = Path(os.getenv('EA_DATA_DIR') or Path.home() / 'TradeEA_data'); data.mkdir(exist_ok=True)
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
                new = []
                if profs:
                    for sym in PAIRS:
                        try:
                            for a in evaluate(Market(sym, b.bars(sym, DAYS)), profs, since):
                                aid = f"{a['profile']}|{a['sym']}|{a['kind']}|{a['side']}|{a['line']}|{a['born']}"
                                if aid in st['sent']:
                                    continue
                                a['jst'] = jst(a['t']); a['id'] = aid; new.append(a)
                        except Exception as ex:
                            logging.warning('%s: %s', sym, ex)
                try:      # GAS: record the alerts, get the app's settings back
                    r = gas.call('eaAlert', {'alerts': [{k: (str(v) if isinstance(v, pd.Timestamp) else (' / '.join(v) if isinstance(v, list) else v)) for k, v in a.items()} for a in new]}, timeout=60)
                    cfg = settings_from(r, cfg)
                except Exception as ex:
                    logging.warning('GAS: %s', ex)
                for a in new:
                    tg.send('alert', text(a), {'notifyAlert': True}); st['sent'].append(a['id'])
                st['sent'] = st['sent'][-5000:]; st['last_bar'] = str(last); first = False
                stf.write_text(json.dumps(st, ensure_ascii=False), encoding='utf-8')
                logging.info('bar %s: %d new alerts (%d profiles on)', last, len(new), len(profs))
        except Exception as ex:
            logging.exception('alerts loop: %s', ex)
        time.sleep(20)


if __name__ == '__main__':
    sys.exit(main())
