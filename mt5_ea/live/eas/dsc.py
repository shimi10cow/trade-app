"""D@B / D@C / D@W: H4 level + M15 Dow turn, scored by the user's lines (2026-11-15, docs/OPEN_ITEMS.md D18 / D19,
docs/DISCRETIONARY_RULES.md). Ported from the research scratch scripts rz18 / rz20 / prep2 / feat_core / add_imp1 / add_feat25 /
strat_trades (the 7 FX pairs EURUSD, USDJPY, AUDJPY, EURJPY, GBPJPY, GBPUSD, AUDUSD).

  Levels : H4 protected levels (押し安値・戻り高値, major and provisional Dow machines, 365 days, until an H4 close beyond) and
           double top / bottom necks (two H4 tops within 2 ATR, 6..60 H4 bars apart, valley >= 1 ATR, the first H4 close beyond the
           neck within 30 bars of the 2nd top; alive 30 days)
  Setup  : a confirmed M15 swing (top) within 0.3 ATR(H4) inside .. 0.6 ATR beyond a level, then an M15 close beyond the M15 swing
           before the top (the neck) within 24 h -> the setup bar (the research entry)
  Scenes : B = the 1st protected level after an H4 major reversal, C = a later one with the pullback < 23.6 % of the H4 trend leg,
           W = a double top / bottom neck (2nd top 0..0.5 ATR inside the 1st, valley < 4.5 ATR, the move before 4..8 ATR)
  Score  : 1 + 2 H4 impulse line effective + D1 impulse line + H1 MA + M15 line broken - opposite level within 2R - steep H4 impulse
           line broken - H4 correction line not yet broken (near) + H1 impulse line when no H4 one; trade only >= 2
  Entry  : the first M15 Dow break (close beyond the M15 swing before the latest counter swing) from the top's bar on, within 2 days;
           stop beyond that counter swing by 0.05 ATR(H4)
  Exit   : no take-profit; stop trailed to confirmed swings formed after the entry: B on H4, C on M15, W on H1 then M15 from +5R, A on H4
           then H1 from +3R
           (buffer 0.1 / 0.05 / 0.02 ATR(H4) for H4 / H1 / M15); no time limit (the 60-day limit was removed 2026-11-17)
  One position per level (while it is open).
2026-11-16 (docs/OPEN_ITEMS.md D19, lab over 20 years): the level must be a band with >= 2 H4 swings (the user's boxes); C exits on M15 (H4 made more but 3 trades
were > 100 % of its profit; M15 keeps +0.26R/trade without the top 5 %, 2026-11-16),
W on H1 then M15 from +5R; W valley < 6 ATR; new scene A = an older level (born before the last H4 major reversal) with such a band,
exit H4 then H1 from +3R.
2026-11-17 (user): B / C skip an entry when the last provisional H4 Dow reversal (a close through the provisional protected swing)
went the other way - a pattern restart does not count (B+C 193 -> 167 trades, +0.90R -> +1.11R/trade, DD -10.8R -> -7.3R).
2026-11-17 (user): an H4 line (protected level / neck) dies only when a whole H4 candle, open and close, is beyond it (a close a little
beyond keeps it), and the line must still be alive at the entry (B / C / W over 20 years: 438 trades +0.90R, +394R, PF 2.70, DD -9.0R,
2 losing years, vs 410 trades +0.87R before). DY@ keeps the H4-close rule.
DY@ (scene 'Y', 2026-11-16, DISCRETIONARY_RULES §13): the levels are every D1 swing (3-bar fractal, 365 days) instead, the band needs
>= 4 H4 swings, no scene / score, the M15 Dow turn within 3 days, exit H4 then H1 from +3R.
DR@ (scene 'R', 2026-11-18, DISCRETIONARY_RULES §14-17): the H4 major protected swings (押し安値 / 戻り高値) only, >= 2 confirmed H4 swings,
<= 30 days after the last H4 major reversal, no broken H4 impulse line, no H4 close beyond the line since it was born, provisional Dow not
against, wick beyond <= 1.0 ATR, no unbroken opposite H4 impulse line; no score; M15 Dow turn within 3 days; exit H4 then H1 from +3R.
17 symbols (not USDJPY; not the other FX crosses, EU indices, oil, gas: tested out of sample and failed). Research parity: 221 / 221 trades.
DX@ (scene 'X', 2026-11-18): H4 gateway return move (see the X_ constants); 13 symbols, indices buy only (run(..., sides=(1,))).
Research parity 108 / 108 trades (+1.01R); live window 28 / 29 entries the same.
Lines are measured in bar time (the chart skips weekends, as MT5 draws them).
"""
import numpy as np
import pandas as pd

from ..core import Frames

TOL, DTOL, DDEP, SCORE_MIN = 0.3, 2.0, 1.0, 2
SYMBOLS = ('EURUSD', 'USDJPY', 'AUDJPY', 'EURJPY', 'GBPJPY', 'GBPUSD', 'AUDUSD')
SCHEME = {'B': [(0, 'H4')], 'C': [(0, 'M15')], 'W': [(0, 'H1'), (5, 'M15')], 'A': [(0, 'H4'), (3, 'H1')], 'Y': [(0, 'H4'), (3, 'H1')],
          'R': [(0, 'H4'), (3, 'H1')], 'X': [(0, 'H4'), (3, 'H1')]}
# DR@ (scene 'R', 2026-11-18, DISCRETIONARY_RULES §14-17): H4 major protected swing (押し安値 / 戻り高値), >= 2 confirmed H4 swings on it,
# <= 30 days after the last H4 major reversal, H4 impulse line not broken, no H4 close beyond the line since it was born, line alive,
# provisional Dow not against, deepest wick beyond the line <= 1.0 ATR(H4), no unbroken opposite H4 impulse line; M15 Dow turn within 3 days
R_TOUCH_MIN, R_DAYS, R_WICK, R_DOW_DAYS = 2, 30, 1.0, 3
# DX@ (scene 'X', 2026-11-18, DISCRETIONARY_RULES §17-18): H4 gateway return move. After an H4 major reversal the gateway is the broken
# protected swing; track the candle extreme after the break; in the return move enter at the M15 Dow turn (close back through the last M15
# counter swing after the extreme), one per return move. Filters: bounce extreme within +-1 ATR of the gateway, origin->gateway < 5 ATR,
# >= 2 H4 swings on the gateway (90 days), no H4 close back beyond it, provisional Dow not against, no unbroken opposite impulse line,
# D score >= 2, H1 MA75 sloping our way with the H1 close beyond it, D1 Dow not against, D1 SMA75 sloping our way with the D1 close beyond
# it, not a double bottom / top reversal (second extreme within 0.5 ATR of the lowest low / highest high before the break). Stop: gateway
# + 0.1 ATR; exit H4 then H1 from +3R; one position per gateway (re-entry after the stop is fine).
X_DAYS, X_GW, X_ORG, X_TOUCH, X_SCORE, X_DBL = 30, 1.0, 5.0, 2, 2, 0.5
R_V = False                         # optional V filter (an M15 higher low / lower high after the top before the entry); 2026-11-18 user: off
Y_TOUCH_MIN, Y_DOW_DAYS = 4, 3     # DY@ (2026-11-16): D1 swing bands with >= 4 H4 swings, the M15 Dow turn within 3 days
TOUCH_MIN = 2                      # 2026-11-16: the level must hold >= 2 H4 swings (within 0.25 ATR, 90 days before the top)
B_FAR = 2.0                        # 2026-11-20 (user): B skips an entry >= 2.0 ATR(H4) from the level (a late entry after the bounce, DISCRETIONARY_RULES 11/20)
BUF = {'H4': 0.1, 'H1': 0.05, 'M15': 0.02}
H = np.timedelta64(1, 'h'); DAY = np.timedelta64(1, 'D'); M15 = np.timedelta64(15, 'm'); BASE = np.datetime64('2000-01-01T00:00', 'ns')


def _atr(b):
    pc = b.c.shift()
    return pd.concat([b.h - b.l, (b.h - pc).abs(), (b.l - pc).abs()], axis=1).max(axis=1).rolling(14).mean().to_numpy()


def _piv(P, PT, T_, Hh, Ll):
    """confirmed pivots -> (confirm time, kind, price, bar time)"""
    ct = np.asarray(PT, dtype='datetime64[ns]'); kd = np.array([q[1] for q in P]); pp = np.array([q[2] for q in P], dtype=float); bt = ct.copy()
    for n in range(len(pp)):
        j = int(np.searchsorted(T_, ct[n], side='right')) - 1; lo = max(0, j - 60)
        arr = (Ll if kd[n] == 'lo' else Hh)[lo:j + 1]; m = np.nonzero(np.isclose(arr, pp[n]))[0]
        if len(m):
            bt[n] = T_[lo + m[-1]]
        else:
            w0 = max(0, j - 24); w = (Ll if kd[n] == 'lo' else Hh)[w0:j + 1]
            if len(w):
                jj = int(np.argmin(w) if kd[n] == 'lo' else np.argmax(w)); bt[n] = T_[w0 + jj]; pp[n] = w[jj]
    return ct, kd, pp, bt


def _mk(TB, dur):
    """calendar time -> bar time (bars evenly spaced, weekends skipped)"""
    TB = np.asarray(TB, dtype='datetime64[ns]'); dur = np.timedelta64(dur, 'ns'); n = len(TB)

    def f(t):
        t = np.asarray(t, dtype='datetime64[ns]'); i = np.clip(np.searchsorted(TB, t, side='right') - 1, 0, n - 1); off = t - TB[i]
        off = np.where((i == n - 1) | (off < np.timedelta64(0, 'ns')), off, np.minimum(off, dur))
        return BASE + i.astype('int64') * dur + off
    return f


def _lines(P, kind, sg, t0, t1, TM, MC, A, tol=0.5):
    """lines from the extreme of the window through later pivots of `kind`, closes kept on the right side (tol ATR)."""
    idx = np.nonzero((P[1] == kind) & (P[3] >= t0) & (P[3] <= t1) & (P[0] <= t1))[0]
    if len(idx) < 2:
        return []
    a = idx[int(np.argmax(P[2][idx]) if sg > 0 else np.argmin(P[2][idx]))]; out = []
    for b in idx:
        if P[3][b] <= P[3][a]:
            continue
        sl = (P[2][b] - P[2][a]) / ((P[3][b] - P[3][a]) / H)
        ka = int(np.searchsorted(TM, P[3][a])); kb = int(np.searchsorted(TM, P[3][b]))
        lv = P[2][a] + sl * ((TM[ka:kb + 1] - P[3][a]) / H)
        if ((MC[ka:kb + 1] - lv) * sg > tol * A).sum() > 0:
            continue
        out.append((a, b, sl))
    return out


def _steepest(c, sg):
    return max(c, key=lambda x: -sg * x[2]) if c else None


def _imp_lines(P, kind, s, te, win, CT, CC, A, tol, minsl, HIx, LOx, TX, conf):
    """impulse lines (2nd point confirmed by a rally of `conf` ATR and a new high, span >= 2 days)"""
    idx = np.nonzero((P[1] == kind) & (P[0] <= te) & (P[3] >= te - win))[0]; out = []
    k = int(np.searchsorted(CT, te, side='right')) - 1
    for ia in range(len(idx)):
        for ib in range(ia + 1, len(idx)):
            a, b = idx[ia], idx[ib]
            if s * (P[2][b] - P[2][a]) <= 0:
                continue
            u = (P[3][b] - P[3][a]) / DAY
            if u <= 0:
                continue
            sl = (P[2][b] - P[2][a]) / u
            if s * sl < minsl * A:
                continue
            jb = int(np.searchsorted(TX, P[3][b])); je = int(np.searchsorted(TX, te))
            if je <= jb + 1:
                continue
            rally = (HIx[jb:je].max() - P[2][b]) if s > 0 else (P[2][b] - LOx[jb:je].min())
            if rally < conf * A:
                continue
            ja = int(np.searchsorted(TX, P[3][a])); prior = HIx[ja:jb + 1].max() if s > 0 else LOx[ja:jb + 1].min()
            if s * ((HIx[jb:je].max() if s > 0 else LOx[jb:je].min()) - prior) <= 0:
                continue
            if u < 2:
                continue
            ka = int(np.searchsorted(CT, P[3][a])); lv = P[2][a] + sl * ((CT[ka:k + 1] - P[3][a]) / DAY)
            broken = bool(((CC[ka:k + 1] - lv) * s < -tol * A).any())
            vv = P[2][a] + sl * ((P[3][idx] - P[3][a]) / DAY); nt = int((np.abs(P[2][idx] - vv) <= 0.3 * A).sum())
            out.append(dict(a=a, b=b, sl=sl, broken=broken, nt=nt, tb=P[3][b]))
    return out


class _Ctx:
    """everything the rules need from a Frames object, built once"""

    def __init__(self, F: Frames):
        self.F = F
        h4 = F.h4.reset_index(drop=True); h1 = F.h1.reset_index(drop=True); m = F.m15_all.reset_index(drop=True)
        self.h4, self.h1 = h4, h1
        self.a4, self.a1 = _atr(h4), _atr(h1)
        self.T4 = h4.t.to_numpy(dtype='datetime64[ns]'); self.C4 = np.asarray(F.C4, dtype='datetime64[ns]')
        self.H4h, self.H4l, self.c4, self.o4 = h4.h.to_numpy(), h4.l.to_numpy(), h4.c.to_numpy(), h4.o.to_numpy()
        self.T1 = h1.t.to_numpy(dtype='datetime64[ns]'); self.C1 = np.asarray(F.C1, dtype='datetime64[ns]')
        self.H1h, self.H1l, self.c1 = h1.h.to_numpy(), h1.l.to_numpy(), h1.c.to_numpy()
        self.CL = np.asarray(F.CL15, dtype='datetime64[ns]'); self.TB = np.asarray(F.M15T, dtype='datetime64[ns]')
        self.O, self.Hm, self.Lm, self.Cm = (np.asarray(x) for x in (F.o, F.h, F.l, F.c))
        self.TM = m.t.to_numpy(dtype='datetime64[ns]'); self.MH, self.ML, self.MC = m.h.to_numpy(), m.l.to_numpy(), m.c.to_numpy()
        self.raw = {'H4': _piv(F.H4P, F.H4PT, self.T4, self.H4h, self.H4l), 'H1': _piv(F.H1P, F.H1PT, self.T1, self.H1h, self.H1l),
                    'M15': _piv(F.P15, F.P15T, self.TB, self.Hm, self.Lm)}
        self.S = {'H4': _mk(self.T4, 4 * H), 'H1': _mk(self.T1, H), 'M15': _mk(self.TB, M15)}
        self.PP = {tf: (self.S[tf](P[0]), P[1], P[2], self.S[tf](P[3])) for tf, P in self.raw.items()}
        cc = {'H4': (self.C4, self.c4), 'H1': (self.C1, self.c1), 'M15': (self.CL, self.Cm)}
        self.CS = {tf: (self.S[tf](c[0]), c[1]) for tf, c in cc.items()}
        self.s20 = h1.c.rolling(20).mean().to_numpy(); self.s75 = h1.c.rolling(75).mean().to_numpy()
        self.PROV = [b[0] for b in F.R4['prov_bars']]
        self.PV = sorted([(self.C4[e['idx']], e['to']) for e in F.R4['all_events'] if e.get('action') == 'REVERSAL' and e.get('machine') == 'prov'])
        # daily bars from H4, 3-bar fractals
        d1 = h4.assign(d=h4.t.dt.floor('D')).groupby('d').agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).reset_index()
        Td = d1.d.to_numpy(dtype='datetime64[ns]'); hd, ld, cd = d1.h.to_numpy(), d1.l.to_numpy(), d1.c.to_numpy(); pts = []
        for i in range(3, len(d1) - 3):
            if ld[i] < ld[i - 3:i].min() and ld[i] <= ld[i + 1:i + 4].min(): pts.append((Td[i] + 4 * DAY, 'lo', ld[i], Td[i]))
            if hd[i] > hd[i - 3:i].max() and hd[i] >= hd[i + 1:i + 4].max(): pts.append((Td[i] + 4 * DAY, 'hi', hd[i], Td[i]))
        pts.sort(key=lambda x: x[3]); sd = _mk(Td, DAY); self.S['D1'] = sd
        self.Pdr = tuple(np.array([x[j] for x in pts]) for j in range(4))
        self.Pd = (sd(self.Pdr[0]), self.Pdr[1], self.Pdr[2], sd(self.Pdr[3])) if pts else self.Pdr
        s50 = pd.Series(cd).rolling(50).mean().to_numpy()
        self.Td, self.Tds, self.cd, self.hd, self.ld, self.ad, self.k50 = Td, sd(Td), cd, hd, ld, _atr(d1), s50 - np.roll(s50, 10)


# ---------------------------------------------------------------- levels and setups (rz18 / rz20)
def _levels(cx: _Ctx, dt: bool, kind='h4'):
    F = cx.F; C4 = cx.C4; LVL = {}
    for e in F.R4['all_events']:
        if e.get('action') != 'breakout_protect' or e.get('machine') not in ('major', 'prov'):
            continue
        kd = 'lo' if e['trend'] == 'up' else 'hi'
        LVL.setdefault((kd, round(e['prot_price'], 8)), (C4[e['idx']], kd, e['prot_price'], e['prot_anchor'], 'prot', 365))
    if kind == 'r':                    # DR@: major protected swings only
        LVL = {}
        for e in F.R4['all_events']:
            if e.get('action') == 'breakout_protect' and e.get('machine') == 'major':
                kd = 'lo' if e['trend'] == 'up' else 'hi'
                LVL.setdefault((kd, round(e['prot_price'], 8)), (C4[e['idx']], kd, float(e['prot_price']), None, 'prot', 365))
    if kind == 'd1':                   # DY@: every D1 swing (3-bar fractal), alive 365 days until an H4 close beyond
        LVL = {}; Pr = cx.Pdr
        for j in range(len(Pr[0])):
            LVL.setdefault((Pr[1][j], round(float(Pr[2][j]), 8)), (Pr[0][j], Pr[1][j], float(Pr[2][j]), Pr[3][j], 'd1', 365))
    if dt:
        LVL = {}
        P4 = cx.raw['H4']; T4 = cx.T4
        for top_k, sgn in (('hi', 1), ('lo', -1)):
            idx = np.nonzero(P4[1] == top_k)[0]
            for a, b in zip(idx[:-1], idx[1:]):
                ka = int(np.searchsorted(T4, P4[3][a])); kb = int(np.searchsorted(T4, P4[3][b]))
                if not (6 <= kb - ka <= 60):
                    continue
                Aa = cx.a4[kb]; p1, p2 = P4[2][a], P4[2][b]
                if not np.isfinite(Aa) or abs(p2 - p1) > DTOL * Aa:
                    continue
                seg = (cx.H4l if sgn > 0 else cx.H4h)[ka:kb + 1]; jn = int(np.argmin(seg) if sgn > 0 else np.argmax(seg)); neck = seg[jn]
                if sgn * (min(p1, p2) if sgn > 0 else max(p1, p2)) - sgn * neck < DDEP * Aa:
                    continue
                kc = int(np.searchsorted(C4, P4[0][b])); ext = max(p1, p2) if sgn > 0 else min(p1, p2); born = None
                for k in range(kc, min(kc + 30, len(cx.c4))):
                    if sgn * (cx.c4[k] - ext) > 0:
                        break
                    if sgn * (cx.c4[k] - neck) < 0:
                        born = k; break
                if born is None:
                    continue
                k0 = max(0, ka - 60)
                rise = sgn * (ext - ((cx.H4l if sgn > 0 else cx.H4h)[k0:ka + 1].min() if sgn > 0 else cx.H4h[k0:ka + 1].max())) / Aa
                LVL[('dt', top_k, round(neck, 8), str(P4[3][b]))] = (C4[born], top_k, float(neck),
                                                                     ('DT' if sgn > 0 else 'DB', P4[3][a], float(p1), P4[3][b], float(p2), rise), 'dt', 30)
    LV = sorted(LVL.values(), key=lambda x: x[0])
    dead = []
    for ct, kd, p, *_ in LV:
        ds = 1 if kd == 'hi' else -1; k0 = int(np.searchsorted(C4, ct, side='right')); beyond = ds * (cx.c4[k0:] - p) > 0
        if kind in ('h4', 'r'):         # 2026-11-17: an H4 line dies only when a whole H4 candle (open and close) is beyond it
            beyond &= ds * (cx.o4[k0:] - p) > 0
        hit = np.nonzero(beyond)[0]
        dead.append(C4[k0 + hit[0]] if len(hit) else np.datetime64('2100-01-01'))
    return LV, np.array(dead, dtype='datetime64[ns]')


def _setups(cx: _Ctx, dt: bool, start, kind='h4'):
    LV, lvl_dead = _levels(cx, dt, kind)
    if not LV:
        return []
    lvl_t = np.array([x[0] for x in LV]); lvl_k = np.array([x[1] for x in LV]); lvl_p = np.array([x[2] for x in LV]); lvl_age = np.array([x[5] for x in LV])
    P15 = cx.raw['M15']; CL, TB, Hm, Lm, Cm = cx.CL, cx.TB, cx.Hm, cx.Lm, cx.Cm; n15 = len(CL); done = set(); rows = []
    # opposite levels for "an opposite level within 2R" come from the protected levels in both cases
    if dt:                              # rz20: the protected levels and the necks together
        LVp, deadp = _levels(cx, False); LVp = LVp + LV; deadp = np.concatenate([deadp, lvl_dead])
    else:
        LVp, deadp = LV, lvl_dead
    pt = np.array([x[0] for x in LVp]); pk = np.array([x[1] for x in LVp]); pp = np.array([x[2] for x in LVp])
    for q in range(len(P15[0])):
        ct, kd, top, tbar = P15[0][q], P15[1][q], P15[2][q], P15[3][q]
        if ct < start:
            continue
        s = -1 if kd == 'hi' else 1
        k4 = int(np.searchsorted(cx.C4, ct, side='right')) - 1; A = cx.a4[k4]; lk = 'hi' if s < 0 else 'lo'
        al = np.nonzero((lvl_k == lk) & (lvl_t < tbar) & (lvl_dead > tbar) & (lvl_t > tbar - lvl_age * DAY))[0]
        if not len(al):
            continue
        d = (top - lvl_p[al]) * (-s) / A; okl = al[(d >= -TOL) & (d <= 0.6)]
        if not len(okl):
            continue
        L = okl[np.argmin(np.abs((top - lvl_p[okl]) / A))]; level = lvl_p[L]; key = (s, L, str(tbar)[:13])
        if key in done:
            continue
        pre = np.nonzero((P15[1] == ('lo' if s < 0 else 'hi')) & (P15[3] < tbar))[0]
        if not len(pre):
            continue
        neck = P15[2][pre[-1]]; i0 = int(np.searchsorted(CL, ct, side='left')); ent_i = None
        for i in range(i0, min(i0 + 96, n15 - 1)):
            if (Hm[i] > top) if s < 0 else (Lm[i] < top):
                break
            if s * (Cm[i] - neck) > 0:
                ent_i = i; break
        if ent_i is None:
            continue
        done.add(key)
        k1 = int(np.searchsorted(cx.C1, CL[ent_i], side='right')) - 1; ent = Cm[ent_i]
        far = max(top, level) if s < 0 else min(top, level); st0 = far - s * 0.1 * cx.a1[k1]; risk = s * (ent - st0)
        if not (0.05 * A <= risk):
            continue
        t = CL[ent_i]
        lows = np.nonzero((P15[1] == ('lo' if s < 0 else 'hi')) & (P15[3] < tbar))[0][-2:]; m15line = False
        if len(lows) == 2 and s * (P15[2][lows[1]] - P15[2][lows[0]]) < 0:
            ta, pa, tb_, pb = P15[3][lows[0]], P15[2][lows[0]], P15[3][lows[1]], P15[2][lows[1]]; hrs = (tb_ - ta) / H
            if hrs > 0:
                m15line = bool(s * (ent - (pb + (pb - pa) / hrs * ((TB[ent_i] - tb_) / H))) > 0)
        ke1 = int(np.searchsorted(cx.C1, t, side='right')) - 1
        ma = bool(s * (cx.s20[k1] - cx.s75[k1]) > 0) or bool(s * (cx.s75[ke1] - cx.s75[ke1 - 5]) > 0)
        op = np.nonzero((pk == ('hi' if s > 0 else 'lo')) & (pt < t) & (deadp > t) & (pt > t - 365 * DAY))[0]; risk_ahead = False
        if len(op):
            ah = (pp[op] - ent) * s; ah = ah[ah > 0]; risk_ahead = bool(len(ah) and ah.min() <= 2 * risk)
        rows.append(dict(t=pd.Timestamp(t), side=s, level=float(level), top=float(top), ttop=pd.Timestamp(tbar), lvl_born=pd.Timestamp(lvl_t[L]), lvl_dead=pd.Timestamp(lvl_dead[L]),
                         anchor=LV[L][3], src=LV[L][4], entry=float(ent), st0=float(st0), risk_atr=float(risk / A), m15line=m15line, ma=ma,
                         risk_ahead=risk_ahead, k4=k4))
    return rows


# ---------------------------------------------------------------- scenes (prep2)
def _scene(cx: _Ctx, r):
    if r['src'] == 'dt':
        typ, t1, p1, t2, p2, rise = r['anchor']; s = r['side']
        kb = int(np.searchsorted(cx.T4, np.datetime64(t2))); A = cx.a4[kb]; A4 = (s * (r['entry'] - r['st0'])) / r['risk_atr']
        ext = max(p1, p2) if typ == 'DT' else min(p1, p2)
        dtop2 = (p2 - p1) / A4 * (1 if typ == 'DT' else -1); depth = abs(ext - r['level']) / A
        return 'W' if (-0.5 <= dtop2 <= 0) and depth < 6 and 4 <= rise < 8 else None
    F = cx.F; C4 = cx.C4; s = r['side']; t = np.datetime64(r['t']); k = int(np.searchsorted(C4, t, side='right')) - 1
    ev = [e for e in F.R4['events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL']
    ek = np.array([e['idx'] for e in ev]); eto = [e['to'] for e in ev]; et = C4[ek] if len(ek) else np.array([], dtype='datetime64[ns]')
    pb = [(C4[e['idx']], 'lo' if e['trend'] == 'up' else 'hi') for e in F.R4['all_events'] if e.get('action') == 'breakout_protect' and e.get('machine') == 'major']
    j = int(np.searchsorted(et, t, side='right')) - 1; tlast = et[j] if j >= 0 else np.datetime64('1900-01-01')
    lk = 'lo' if s > 0 else 'hi'; born = np.datetime64(r['lvl_born'])
    n_since = sum(1 for tt, kk in pb if kk == lk and tlast < tt <= born)
    if n_since == 1:
        return 'B'
    if n_since == 0:
        return 'A'                     # 2026-11-16: an older level (born before the last H4 major reversal), a band touched >= 2 times
    if n_since < 2:
        return None
    jj = int(np.searchsorted(ek, k, side='right')) - 1
    if jj >= 1 and (eto[jj] == 'up') == (s > 0):
        a, b = ek[jj - 1], ek[jj]; org = (cx.H4l[a:b + 1].min() if s > 0 else cx.H4h[a:b + 1].max())
        ext = (cx.H4h[b:k + 1].max() if s > 0 else cx.H4l[b:k + 1].min()); leg = s * (ext - org)
        ret4 = s * (ext - r['top']) / leg if leg > 0 else np.nan
        if ret4 < 0.236:
            return 'C'
    return None


# ---------------------------------------------------------------- score parts (feat_core.trade, add_imp1)
def _score(cx: _Ctx, r):
    s = r['side']; te = np.datetime64(r['t']); k = int(np.searchsorted(cx.C4, te, side='right')) - 1; A = cx.a4[k]; risk = s * (r['entry'] - r['st0'])
    S = cx.S; kind = 'hi' if s > 0 else 'lo'; out = {}
    # correction lines (H4 / H1 / M15) from the pullback's extreme since the level was born
    k4 = int(np.searchsorted(cx.T4, np.datetime64(r['lvl_born'])))
    if k4 >= k or k4 < 0:
        k4 = max(0, k - 60)
    seg = (cx.H4h if s > 0 else cx.H4l)[k4:k + 1]; cst = cx.T4[k4 + int(np.argmax(seg) if s > 0 else np.argmin(seg))]; D = {}
    for tf in ('H4', 'H1', 'M15'):
        P = cx.PP[tf]; CT, Cc = cx.CS[tf]; ts = S[tf](te)
        t0 = S[tf](max(cst, te - 2 * DAY)) if tf == 'M15' else S[tf](cst - 4 * H)
        cl = [x for x in _lines(P, kind, s, t0, ts, CT, Cc, A) if s * (P[2][x[1]] - P[2][x[0]]) < 0]; b = _steepest(cl, s)
        D[tf] = np.nan if not b else s * ((P[2][b[0]] + b[2] * ((ts - P[3][b[0]]) / H)) - r['entry']) / risk
    m3 = 0.3 / r['risk_atr']
    h4near = (not np.isnan(D['H4'])) and (D['H4'] >= -m3) and D['H4'] < 2
    # H4 impulse line
    S4 = S['H4']; ts = S4(te); e = int(np.searchsorted(cx.TM, te)); w = max(0, e - 96)
    jx = w + int(np.argmin(cx.ML[w:e]) if s > 0 else np.argmax(cx.MH[w:e])); ext = (cx.ML if s > 0 else cx.MH)[jx]; text = S4(cx.TM[jx])
    want = 'up' if s > 0 else 'down'; cand = [tt for tt, to in cx.PV if to == want and tt < te]
    t0 = max((cand[-1] - 10 * DAY) if cand else te - 60 * DAY, te - 120 * DAY)
    P = cx.PP['H4']; C4s, c4 = cx.CS['H4']; T4s = S4(cx.T4); win = ts - S4(t0)
    L = _imp_lines(P, 'lo' if s > 0 else 'hi', s, ts, win, C4s, c4, A, 0.3, 0.2, cx.H4h, cx.H4l, T4s, 1.0); ok = [x for x in L if not x['broken']]
    imp4 = False
    if ok:
        c = max(ok, key=lambda x: (x['nt'], x['tb'])); v = P[2][c['a']] + c['sl'] * ((text - P[3][c['a']]) / DAY); imp4 = bool(abs(s * (ext - v) / A) <= 1.0)
    L5 = _imp_lines(P, 'lo' if s > 0 else 'hi', s, ts, win, C4s, c4, A, 0.5, 0.2, cx.H4h, cx.H4l, T4s, 1.0)
    st = sorted(L5, key=lambda x: (x['tb'], s * x['sl']), reverse=True); impbrk = False
    if st and st[0]['broken']:
        sb = st[0]; vnow = P[2][sb['a']] + sb['sl'] * ((ts - P[3][sb['a']]) / DAY); jb = int(np.searchsorted(T4s, P[3][sb['b']])); je = int(np.searchsorted(T4s, ts))
        lowest = (cx.H4l[jb + 1:je].min() if s > 0 else cx.H4h[jb + 1:je].max()) if je > jb + 1 else P[2][sb['b']]
        impbrk = bool(s * (r['entry'] - vnow) <= 0 and s * (lowest - P[2][sb['b']]) < 0)
    # D1 impulse line
    Pd = cx.Pd; kd = int(np.searchsorted(cx.Td + DAY, te, side='right')) - 1; Ad = cx.ad[kd]
    exd = (cx.ld if s > 0 else cx.hd)[max(0, kd - 2):kd + 1]; exd = exd.min() if s > 0 else exd.max(); tds = S['D1'](te)
    Ld = _imp_lines(Pd, 'lo' if s > 0 else 'hi', s, tds, 90 * DAY, cx.Tds + DAY, cx.cd, Ad, 0.5, 0.02, cx.hd, cx.ld, cx.Tds, 1.0) if len(Pd[0]) else []
    okd = []
    for x in Ld:
        if (x['tb'] - Pd[3][x['a']]) / DAY < 10:
            continue
        ja = int(np.searchsorted(cx.Tds, Pd[3][x['a']])); jb = int(np.searchsorted(cx.Tds, Pd[3][x['b']]))
        if ((cx.hd[ja:jb + 1].max() - Pd[2][x['b']]) if s > 0 else (Pd[2][x['b']] - cx.ld[ja:jb + 1].min())) >= Ad:
            okd.append(x)
    okn = [x for x in okd if not x['broken']]; cdl = max(okn, key=lambda x: (x['tb'], -s * x['sl'])) if okn else None; impd = False
    if cdl:
        v = Pd[2][cdl['a']] + cdl['sl'] * ((cx.Tds[kd] - Pd[3][cdl['a']]) / DAY); impd = bool(abs(s * (exd - v) / Ad) <= 0.5 and s * cx.k50[kd] > 0)
    # H1 impulse line when no H4 one can be drawn (+1)
    imp1 = False
    if not any(not x['broken'] for x in L):
        S1 = S['H1']; P1 = cx.PP['H1']
        L1 = _imp_lines(P1, 'lo' if s > 0 else 'hi', s, S1(te), 15 * DAY, cx.CS['H1'][0], cx.CS['H1'][1], A, 0.2, 0.3, cx.H1h, cx.H1l, S1(cx.T1), 0.5)
        ok1 = [x for x in L1 if not x['broken']]
        if ok1:
            c = max(ok1, key=lambda x: (x['nt'], x['tb'])); v = P1[2][c['a']] + c['sl'] * ((S1(cx.TM[jx]) - P1[3][c['a']]) / DAY)
            imp1 = bool(abs(s * (ext - v)) <= 0.5 * A)
    out = dict(imp4=imp4, impd=impd, impbrk=impbrk, h4near=h4near, imp1=imp1)
    out['score'] = 1 + 2 * imp4 + impd + r['ma'] + r['m15line'] - r['risk_ahead'] - impbrk - h4near + imp1
    return out


def _touches(cx: _Ctx, r, q):
    """H4 swings within 0.25 ATR(H4) of the level in the 90 days before the top (A at the M15 Dow entry).
    2026-11-17: only swings already confirmed at the entry (P[0] <= entry time). Live only ever has confirmed swings, so this changes
    the backtest only (it used to count the swing still forming at the touch)."""
    te = cx.TM[q] + M15; k = int(np.searchsorted(cx.C4, te, side='right')) - 1; A = cx.a4[k]; P = cx.raw['H4']; tt0 = np.datetime64(r['ttop'])
    m = np.nonzero((P[3] < tt0) & (P[3] >= tt0 - 90 * DAY) & (P[0] <= te))[0]
    return int((np.abs(P[2][m] - r['level']) <= 0.25 * A).sum())


# ---------------------------------------------------------------- M15 Dow entry (add_feat25)
def _dow_entry(cx: _Ctx, r, days=2):
    s = r['side']; P = cx.raw['M15']; TM, MC = cx.TM, cx.MC; CLm = TM + M15
    tq0 = np.datetime64(r['ttop']); q0 = int(np.searchsorted(TM, tq0)); q1 = min(int(np.searchsorted(TM, tq0 + days * DAY)), len(TM) - 1)
    k = int(np.searchsorted(cx.C4, np.datetime64(r['t']), side='right')) - 1; A = cx.a4[k]
    ctr, base = ('lo', 'hi') if s > 0 else ('hi', 'lo')
    for q in range(q0 + 1, q1):
        tq = CLm[q - 1]; okp = np.nonzero((P[0] <= tq) & (P[3] >= tq0 - 12 * H))[0]
        ic = [x for x in okp if P[1][x] == ctr]
        if not ic:
            continue
        ic = ic[-1]; ib = [x for x in okp if P[1][x] == base and P[3][x] < P[3][ic]]
        if not ib:
            continue
        lvl = P[2][ib[-1]]
        if s * (MC[q] - lvl) > 0 and s * (MC[q - 1] - lvl) <= 0:
            ent = MC[q]; st = P[2][ic] - s * 0.05 * A
            return (q, ent, st) if s * (ent - st) > 0 else None
    return None


def _signals_r(cx: _Ctx, start):
    """DR@ setups (scene 'R'); same filters as the research form2 (scratchpad q20/form2.py, touch_confirmed=True)"""
    F = cx.F; out = []
    rv = np.array([cx.C4[e['idx']] for e in F.R4['events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL'], dtype='datetime64[ns]')
    pv = sorted((cx.C4[e['idx']], e['to']) for e in F.R4['all_events'] if e.get('machine') == 'prov' and e['action'] == 'REVERSAL')
    pvt = np.array([a for a, _ in pv], dtype='datetime64[ns]'); pvto = [b for _, b in pv]
    S4 = cx.S['H4']; P4 = cx.PP['H4']; C4s, c4s = cx.CS['H4']; T4s = S4(cx.T4)
    for r in _setups(cx, False, start, 'r'):
        de = _dow_entry(cx, r, R_DOW_DAYS)
        if de is None:
            continue
        q, ent, stp = de; te = cx.TM[q] + M15
        n = _touches(cx, r, q)
        if n < R_TOUCH_MIN:
            continue
        j = int(np.searchsorted(rv, te, side='right')) - 1
        if j < 0 or (te - rv[j]) / DAY > R_DAYS:
            continue
        if np.datetime64(r['lvl_dead']) <= te:
            continue
        sp = _score(cx, dict(r, entry=float(ent)))
        if sp['impbrk']:
            continue
        s_ = r['side']; lv = r['level']; k = int(np.searchsorted(cx.C4, te, side='right')) - 1; A = cx.a4[k]
        kb = int(np.searchsorted(cx.C4, np.datetime64(r['lvl_born']), side='right')); kt = int(np.searchsorted(cx.C4, te, side='right'))
        if (s_ * (cx.c4[kb:kt] - lv) < 0).any():
            continue                   # an H4 close beyond the line since it was born
        w_ = (cx.H4l if s_ > 0 else cx.H4h)[kb:kt]
        if len(w_) and max(0.0, float(np.max(-s_ * (w_ - lv)))) / A > R_WICK:
            continue
        jp = int(np.searchsorted(pvt, te, side='right')) - 1
        if jp >= 0 and (pvto[jp] == 'up') != (s_ > 0):
            continue                   # provisional Dow against
        ts = S4(te); so = -s_
        L = _imp_lines(P4, 'lo' if so > 0 else 'hi', so, ts, ts - S4(te - 60 * DAY), C4s, c4s, A, 0.3, 0.2, cx.H4h, cx.H4l, T4s, 1.0)
        if any(not y['broken'] for y in L):
            continue                   # an opposite H4 impulse line still unbroken
        if R_V:
            P15 = cx.raw['M15']; tt0 = np.datetime64(r['ttop'])
            hl = np.nonzero((P15[1] == ('lo' if s_ > 0 else 'hi')) & (P15[3] > tt0) & (P15[0] <= te))[0]
            if not (len(hl) and (s_ * (P15[2][hl] - r['top']) > 0).any()):
                continue
        out.append(dict(r, score=n, scene='R', q=q, sig_t=pd.Timestamp(te), dow_entry=float(ent), dow_stop=float(stp),
                        lvl_key=(r['side'], round(r['level'], 8))))
    return out


def _signals_x(cx: _Ctx, start):
    """DX@ setups (scene 'X'); same steps as the research (scratchpad q20: dx3.py, dx3f.py, dx3tp.py, d1ma2.py, dbot2.py, dx_line.py)"""
    F = cx.F; out = []; allev = F.R4['all_events']
    rv = [e for e in allev if e.get('machine') == 'major' and e['action'] == 'REVERSAL']
    rp = {e['idx']: e for e in allev if e.get('machine') == 'major' and str(e['action']).startswith('reversal_protect')}
    rvt = np.array([cx.C4[e['idx']] for e in rv], dtype='datetime64[ns]')
    pv = sorted((cx.C4[e['idx']], e['to']) for e in allev if e.get('machine') == 'prov' and e['action'] == 'REVERSAL')
    pvt = np.array([a for a, _ in pv], dtype='datetime64[ns]'); pvto = [b for _, b in pv]
    LV, dead = _levels(cx, False); lt = np.array([x[0] for x in LV]); lk = np.array([x[1] for x in LV]); lp = np.array([x[2] for x in LV])
    S4 = cx.S['H4']; P4 = cx.PP['H4']; C4s, c4s = cx.CS['H4']; T4s = S4(cx.T4); P4r = cx.raw['H4']; P15 = cx.raw['M15']
    conf, kinds, prices, tops = P15; TM, MC, MH, ML = cx.TM, cx.MC, cx.MH, cx.ML; CLm = TM + M15
    s75d = pd.Series(cx.cd).rolling(75).mean().to_numpy(); Pdr = cx.Pdr
    for j, e in enumerate(rv):
        tr = rvt[j]
        if tr < start:
            continue
        s = 1 if e['to'] == 'up' else -1; G = float(e['broken_price']); kr = e['idx']
        O = float(rp[kr]['prot_price']) if kr in rp and rp[kr].get('prot_price') is not None else None
        # double bottom / top before the break: lowest low (highest high) since the gateway formed, then a second one within 0.5 ATR
        ka = int(e['broken_anchor']) if e.get('broken_anchor') is not None else max(0, kr - 60)
        seg = (cx.H4l if s > 0 else cx.H4h)[ka:kr + 1]; jx = ka + int(np.argmin(seg) if s > 0 else np.argmax(seg)); O2 = float(seg.min() if s > 0 else seg.max())
        mm = np.nonzero((P4r[1] == ('lo' if s > 0 else 'hi')) & (P4r[3] > cx.T4[jx]) & (P4r[0] <= tr))[0]; px = P4r[2][mm]
        if ((s * (px - O2) > 0) & (np.abs(px - O2) <= X_DBL * cx.a4[kr])).any():
            continue
        if O is None or abs(G - O) / cx.a4[kr] >= X_ORG:
            continue
        tend = min(rvt[j + 1] if j + 1 < len(rv) else np.datetime64('2100-01-01'), tr + X_DAYS * DAY)
        q = int(np.searchsorted(TM, tr)); qend = int(np.searchsorted(TM, tend))
        ext = None; ext_q = None; used = False
        sl = np.nonzero((tops >= tr - DAY) & (tops <= tend))[0]; c_, k_, p_, t_ = conf[sl], kinds[sl], prices[sl], tops[sl]
        while q < min(qend, len(TM) - 1):
            te = CLm[q]; k = int(np.searchsorted(cx.C4, te, side='right')) - 1
            if k >= 1 and cx.C4[k] <= te and -s * (cx.c4[k] - G) > 0 and -s * (cx.o4[k] - G) > 0 and cx.C4[k] > tr:
                break                          # the gateway died (a whole H4 candle back beyond it)
            lq = ML[q] if s < 0 else MH[q]
            if ext is None or (s < 0 and lq < ext) or (s > 0 and lq > ext):
                ext = lq; ext_q = q; used = False
            if not used and ext_q is not None:
                m = (c_ <= te) & (t_ > TM[ext_q]); ic = np.nonzero(m & (k_ == ('lo' if s < 0 else 'hi')))[0]; io = np.nonzero(m & (k_ == ('hi' if s < 0 else 'lo')))[0]
                if len(ic) and len(io):
                    lv = p_[ic[-1]]
                    if s * (MC[q] - lv) > 0 and s * (MC[q - 1] - lv) <= 0:
                        used = True; A = cx.a4[k]; bseg = (MH if s < 0 else ML)[ext_q:q + 1]; jt = ext_q + int(np.argmax(bseg) if s < 0 else np.argmin(bseg))
                        bh = float(bseg.max() if s < 0 else bseg.min()); stp = bh - s * 0.05 * A; ent = float(MC[q]); risk = s * (ent - stp)
                        x = _x_ok(cx, s, te, tr, G, A, k, bh, stp, ent, risk, TM[jt], P4r, P15, pvt, pvto, lt, lk, lp, dead, S4, P4, C4s, c4s, T4s, Pdr, s75d)
                        if x is not None:
                            gs = G - s * 0.1 * A
                            if s * (ent - gs) > 0.05 * A:
                                out.append(dict(side=s, level=G, scene='X', q=q, sig_t=pd.Timestamp(te), dow_entry=ent, dow_stop=float(gs), score=x,
                                                lvl_key=('X', s, str(tr)), lvl_dead=pd.Timestamp('2100-01-01')))
            q += 1
    return out


def _x_ok(cx, s, te, tr, G, A, k, bh, stp, ent, risk, ttop, P4r, P15, pvt, pvto, lt, lk, lp, dead, S4, P4, C4s, c4s, T4s, Pdr, s75d):
    """DX@ filters for one candidate; returns the D score when it passes, else None"""
    if risk <= 0.05 * A or not (-X_GW <= -s * (bh - G) / A <= X_GW):
        return None
    m = np.nonzero((P4r[3] < te) & (P4r[3] >= te - 90 * DAY) & (P4r[0] <= te))[0]
    if int((np.abs(P4r[2][m] - G) <= 0.25 * A).sum()) < X_TOUCH:
        return None
    kb = int(np.searchsorted(cx.C4, tr, side='right')); kt = int(np.searchsorted(cx.C4, te, side='right'))
    if (-s * (cx.c4[kb:kt] - G) > 0).any():
        return None
    jp = int(np.searchsorted(pvt, te, side='right')) - 1
    if jp >= 0 and (pvto[jp] == 'up') != (s > 0):
        return None
    k1 = int(np.searchsorted(cx.C1, te, side='right')) - 1
    if not (s * (cx.s75[k1] - cx.s75[max(0, k1 - 5)]) > 0 and s * (cx.c1[k1] - cx.s75[k1]) > 0):
        return None
    mk = Pdr[0] <= te; kk = Pdr[1][mk]; vv = Pdr[2][mk]; hh = vv[kk == 'hi'][-2:]; ll = vv[kk == 'lo'][-2:]; d1 = 0
    if len(hh) == 2 and len(ll) == 2:
        d1 = 1 if (hh[1] > hh[0] and ll[1] > ll[0]) else (-1 if (hh[1] < hh[0] and ll[1] < ll[0]) else 0)
    if d1 * s < 0:
        return None
    kd = int(np.searchsorted(cx.Td + DAY, te, side='right')) - 1
    if kd < 10 or not np.isfinite(s75d[kd - 10]) or not (s * (s75d[kd] - s75d[kd - 10]) > 0 and s * (cx.cd[kd] - s75d[kd]) > 0):
        return None
    ts = S4(te); so = -s
    L = _imp_lines(P4, 'lo' if so > 0 else 'hi', so, ts, ts - S4(te - 60 * DAY), C4s, c4s, A, 0.3, 0.2, cx.H4h, cx.H4l, T4s, 1.0)
    if any(not y['broken'] for y in L):
        return None
    # D score (as dsc._setups / _score) with the bounce-extreme stop
    k1t = int(np.searchsorted(cx.C1, np.datetime64(ttop), side='right')) - 1
    ma = bool(s * (cx.s20[k1t] - cx.s75[k1t]) > 0) or bool(s * (cx.s75[k1] - cx.s75[k1 - 5]) > 0)
    lows = np.nonzero((P15[1] == ('lo' if s < 0 else 'hi')) & (P15[3] < ttop))[0][-2:]; m15line = False
    if len(lows) == 2 and s * (P15[2][lows[1]] - P15[2][lows[0]]) < 0:
        ta, pa, tb_, pb = P15[3][lows[0]], P15[2][lows[0]], P15[3][lows[1]], P15[2][lows[1]]; hrs = (tb_ - ta) / H
        if hrs > 0:
            m15line = bool(s * (ent - (pb + (pb - pa) / hrs * ((te - M15 - tb_) / H))) > 0)
    op = np.nonzero((lk == ('hi' if s > 0 else 'lo')) & (lt < te) & (dead > te) & (lt > te - 365 * DAY))[0]; ra = False
    if len(op):
        ah = (lp[op] - ent) * s; ah = ah[ah > 0]; ra = bool(len(ah) and ah.min() / risk <= 2)
    sp = _score(cx, dict(side=s, t=pd.Timestamp(te), entry=ent, st0=stp, risk_atr=risk / A, lvl_born=pd.Timestamp(tr), ma=ma, m15line=m15line, risk_ahead=ra))
    return int(sp['score']) if sp['score'] >= X_SCORE else None


def signals(F: Frames, start=None, kind='h4'):
    """all scored setups with their scene and M15 Dow entry: list of dict(t, side, scene, entry, stop, level_key, q)"""
    cx = _Ctx(F); start = np.datetime64(start if start is not None else F.START); out = []
    if kind == 'r':
        return cx, _signals_r(cx, start)
    if kind == 'x':
        return cx, _signals_x(cx, start)
    if kind == 'd1':                   # DY@: no scene, no score; the band needs >= Y_TOUCH_MIN H4 swings
        for r in _setups(cx, False, start, 'd1'):
            de = _dow_entry(cx, r, Y_DOW_DAYS)
            if de is None:
                continue
            q, ent, st = de
            if _touches(cx, r, q) < Y_TOUCH_MIN:
                continue
            out.append(dict(r, score=0, scene='Y', q=q, sig_t=pd.Timestamp(cx.TM[q] + M15), dow_entry=float(ent), dow_stop=float(st),
                            lvl_key=(r['side'], round(r['level'], 8))))
        return cx, out
    for dt in (False, True):
        for r in _setups(cx, dt, start):
            sc = _scene(cx, r)
            if sc is None:
                continue
            sp = _score(cx, r)
            if sp['score'] < SCORE_MIN:
                continue
            de = _dow_entry(cx, r)
            if de is None:
                continue
            q, ent, st = de
            if _touches(cx, r, q) < TOUCH_MIN:
                continue
            out.append(dict(r, **sp, scene=sc, q=q, sig_t=pd.Timestamp(cx.TM[q] + M15), dow_entry=float(ent), dow_stop=float(st),
                            lvl_key=(r['side'], round(r['level'], 8))))
    return cx, out


def run(F: Frames, scene, env=None, start=None, horizon_days=None, sides=None):
    """dict(trades, open, pending) for one scene ('B' / 'C' / 'W'); entries at the M15 Dow break bar's close (research; `t` = that
    close time); a signal on the last closed bar is `pending` (signal_t = its open time, enter at the next open with the stop `sl`).
    Closed trades: why = 'stop' (trailed stop hit); 'time' only when horizon_days is given (no limit by default since 2026-11-17)."""
    cache = F.__dict__.setdefault('_dsc', {})                 # B / C / W share one pass over the setups
    kind = {'Y': 'd1', 'R': 'r', 'X': 'x'}.get(scene, 'h4')
    if (start, kind) not in cache:
        cache[(start, kind)] = signals(F, start, kind)
    cx, sig = cache[(start, kind)]
    sig = sorted([x for x in sig if x['scene'] == scene and (sides is None or x['side'] in sides)], key=lambda x: (x['sig_t'], x['side']))   # sides: DX@ indices buy only
    TM, MH, ML, MC = cx.TM, cx.MH, cx.ML, cx.MC; last = len(TM) - 1; busy = {}; seen = set(); trades, opened, pending = [], [], []
    pv = sorted((cx.C4[e['idx']], e['to']) for e in cx.F.R4['all_events'] if e.get('machine') == 'prov' and e['action'] == 'REVERSAL')
    pvt = np.array([a for a, _ in pv], dtype='datetime64[ns]'); pvto = [b for _, b in pv]
    for x in sig:
        key = (x['sig_t'], x['side'])
        if key in seen:
            continue
        seen.add(key)
        if x['lvl_key'] in busy and busy[x['lvl_key']] > np.datetime64(x['sig_t']):
            continue
        if kind == 'h4' and np.datetime64(x['lvl_dead']) <= np.datetime64(x['sig_t']):
            continue                   # 2026-11-17: the line must still be alive at the entry
        if scene in ('B', 'C'):        # 2026-11-17: skip when the last provisional H4 Dow reversal (close through the provisional
            j = int(np.searchsorted(pvt, np.datetime64(x['sig_t']), side='right')) - 1     # protected swing) went against us
            if j >= 0 and (pvto[j] == 'up') != (x['side'] > 0):
                continue
        s = x['side']; q0 = x['q'] + 1; ent, st = x['dow_entry'], x['dow_stop']; risk = s * (ent - st)
        k = int(np.searchsorted(cx.C4, np.datetime64(x['sig_t']), side='right')) - 1; A = cx.a4[k]
        if scene == 'B' and s * (ent - x['level']) / A >= B_FAR:
            continue
        if x['q'] == last:
            pending.append(dict(signal_t=pd.Timestamp(TM[x['q']]), side=s, sl=st, entry=ent, scene=scene, tag=f"D{scene} score {int(x['score'])}")); continue
        q1 = last + 1 if horizon_days is None else min(int(np.searchsorted(TM, TM[x['q']] + horizon_days * DAY)), last + 1);   # 2026-11-17: no 60-day limit
        best = 0.0; tf_i = 0; sch = SCHEME[scene]; ex = None
        for q in range(q0, q1):
            if (ML[q] <= st) if s > 0 else (MH[q] >= st):
                ex = st; break
            best = max(best, s * ((MH[q] if s > 0 else ML[q]) - ent) / risk)
            while tf_i + 1 < len(sch) and best >= sch[tf_i + 1][0]:
                tf_i += 1
            tf = sch[tf_i][1]; P = cx.raw[tf]
            idx = np.nonzero((P[1] == ('lo' if s > 0 else 'hi')) & (P[0] <= TM[q] + M15) & (P[3] >= np.datetime64(x['sig_t'])))[0]
            if len(idx):
                cand = P[2][idx[-1]] - s * BUF[tf] * A
                if s * (cand - st) > 0:
                    st = cand
        rec = dict(t=x['sig_t'], side=s, scene=scene, entry=ent, stop0=x['dow_stop'], risk=risk, score=int(x['score']), level=x['level'])
        if ex is None and q1 > last:
            opened.append(dict(rec, sl=st)); busy[x['lvl_key']] = np.datetime64('2100-01-01'); continue
        why = 'stop'
        if ex is None:
            ex = MC[q1 - 1]; q = q1 - 1; why = 'time'
        R = s * (ex - ent) / risk - cx.F.COST / risk
        trades.append(dict(rec, exit=float(ex), exit_t=pd.Timestamp(TM[q]), R=float(R), why=why)); busy[x['lvl_key']] = TM[q]
    return dict(trades=pd.DataFrame(trades), open=opened, pending=pending)
