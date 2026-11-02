"""Round 7 (EURUSD / XAUUSD): two axes, trades saved with their features for narrowing (choose on the first half).

TREND: TR (TR2 + M15 trend) and the M5 close breaking the M15 counter line (round 6 'TL'). Stop 3 ATR15 (A3) or 4 ATR15 (A4).
       Exits: from +1.5R trail M5 swings, up to 24h / 72h; from +1R trail M15 swings up to 72h; from +1R trail H1-like swings
       (M15 ZigZag at 3x) up to 120h.
       Features: pullback number, hours since the H1 regime began, impulse (regime start extreme -> the line's first high) in H1 ATR,
       pullback depth as a share of the impulse, line span (M15 bars) and steepness, H1 MA75 slope, H4 opening / slope, H1 MA20 distance.
RANGE: H4 MA75 flat (|10-bar slope| < 0.15 ATR4) and H1 ER48 < 0.15; only the daily-side direction; price in the lower (upper for
       sells) 35% of the 48-bar H1 range; M5 trigger TL / D5 (as round 6). Stop: below the 48-bar H1 low by 0.3 ATR(H1).
       Exits: target the range middle or the far side (95%), or from +1R trail M5 swings; up to 72h.
"""
import numpy as np, pandas as pd, numba as nb
from sim import COST, SPLIT, build
from sim5 import zig
from sim6 import zigx

@nb.njit(cache=True)
def run(ent, side, stop, tgt, o, h, l, c, swh, swl, gap, maxb, arm, trail):
    n = len(o); R = np.full(len(ent), np.nan); X = np.zeros(len(ent), np.int64); ends = np.full(2, -1)
    for k in range(len(ent)):
        e = ent[k]
        if e >= n: continue
        slot = -1
        for q in range(2):
            if ends[q] < e: slot = q; break
        if slot < 0: continue
        s = side[k]; en = o[e]; st = stop[k]; risk = (en - st) * s; tp = tgt[k]
        if risk <= 0: continue
        if np.isfinite(tp) and (tp - en) * s <= 0: continue
        j = e; ex = np.nan; armed = False
        while True:
            if s == 1 and l[j] <= st: ex = min(st, o[j]); break
            if s == -1 and h[j] >= st: ex = max(st, o[j]); break
            if np.isfinite(tp):
                if s == 1 and h[j] >= tp: ex = max(tp, o[j]); break
                if s == -1 and l[j] <= tp: ex = min(tp, o[j]); break
            if j - e >= maxb or j + 1 >= n or gap[j + 1]: ex = c[j]; break
            if trail:
                if not armed and ((h[j] if s == 1 else l[j]) - en) * s >= arm * risk: armed = True
                if armed:
                    nsw = swl[j] if s == 1 else swh[j]
                    if np.isfinite(nsw) and (nsw - st) * s > 0 and (c[j] - nsw) * s > 0: st = nsw
            j += 1
        R[k] = (ex - en) * s / risk; X[k] = j; ends[slot] = j
    return R, X

def atr7(h, l, c):
    pc = np.r_[c[0], c[:-1]]
    return pd.Series(np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))).ewm(alpha=1 / 7, adjust=False).mean().to_numpy()

@nb.njit(cache=True)
def zig3(h, l, a7, k):
    n = len(h); sh = np.full(n, np.nan); sl = np.full(n, np.nan); d = 1; ext = h[0]; lh = np.nan; ll = np.nan
    for i in range(1, n):
        th = k * a7[i]
        if d == 1:
            if h[i] >= ext: ext = h[i]
            elif l[i] <= ext - th: lh = ext; d = -1; ext = l[i]
        else:
            if l[i] <= ext: ext = l[i]
            elif h[i] >= ext + th: ll = ext; d = 1; ext = h[i]
        sh[i] = lh; sl[i] = ll
    return sh, sl

def main():
    rows = []
    for sym in ('EURUSD', 'XAUUSD'):
        f, ok, gap15, ctx, trg = build(sym); n = len(f)
        c = f.c.to_numpy(); m20 = f.m20.to_numpy(); m75 = f.m75.to_numpy(); a = f.a15.to_numpy()
        h15, l15 = f.h.to_numpy(), f.l.to_numpy()
        reg = np.sign(f.h1m20 - f.h1m75).fillna(0).to_numpy()
        ep = np.zeros(n); rs = np.zeros(n, np.int64); cur = 0; k = 0; armed = False; start = 0
        for i in range(1, n):
            if reg[i] != cur: cur = reg[i]; k = 0; armed = True; start = i
            if cur != 0:
                if (c[i] - m20[i]) * cur >= 2 * a[i]: armed = True
                if armed and trg[('MA', int(cur))][i]: k += 1; armed = False
            ep[i] = k; rs[i] = start
        a7 = atr7(h15, l15, c); ZH, ZL = zigx(h15, l15, a7)
        bh, bl = zig3(h15, l15, a7, 6.0)                     # bigger M15 swings (~H1 dow) for the long trail
        m15tr = {s: ((m20 - m75) * s > 0) & (f.dow15.to_numpy() == s) for s in (1, -1)}
        m5 = pd.read_pickle(f'/home/user/trendlab/st/m5/m5_{sym}.pkl').reset_index(drop=True)
        t5 = m5.time.to_numpy(); o5, h5, l5, c5 = (m5[x].to_numpy(float) for x in ('open', 'high', 'low', 'close')); N = len(t5)
        sh5, sl5 = zig(h5, l5, atr7(h5, l5, c5))
        gap5 = np.r_[False, np.diff(t5).astype('timedelta64[m]').astype(int) > 180]
        ct15 = (f.time + pd.Timedelta('15min')).to_numpy(); p = np.searchsorted(ct15, t5 + np.timedelta64(5, 'm'), side='right') - 1
        okp = p >= 0; p = np.maximum(p, 0)
        hr5 = pd.DatetimeIndex(t5).hour.to_numpy(); ok5 = okp & ok[p] & ~np.isin(hr5, (20, 21, 22))
        A15 = a[p]; M20 = m20[p]
        sh15m, sl15m = f.sh.to_numpy()[p], f.sl.to_numpy()[p]; bhm, blm = bh[p], bl[p]
        dw = np.zeros(N); d = 0
        for i in range(1, N):
            if np.isfinite(sh5[i - 1]) and c5[i] > sh5[i - 1]: d = 1
            elif np.isfinite(sl5[i - 1]) and c5[i] < sl5[i - 1]: d = -1
            dw[i] = d
        touch = {1: pd.Series(l5 <= M20).rolling(12).max().to_numpy() > 0, -1: pd.Series(h5 >= M20).rolling(12).max().to_numpy() > 0}
        pos15 = p + ((t5 - f.time.to_numpy()[p]).astype('timedelta64[m]').astype(float) / 15.0)
        cumlo = pd.Series(l15); cumhi = pd.Series(h15)
        H1A = f.h1a.to_numpy()[p]; HI = f.h1hi.to_numpy()[p]; LO = f.h1lo.to_numpy()[p]
        rng_pos = (c5 - LO) / (HI - LO)
        tl, d5 = {}, {}
        for s in (1, -1):
            Z = ZH if s == 1 else ZL
            v1, i1, v0, i0 = Z[p, 0], Z[p, 1], Z[p, 2], Z[p, 3]
            good = np.isfinite(v0) & ((v1 - v0) * s < 0) & (i1 > i0)
            slope = (v1 - v0) / np.where(good, i1 - i0, 1); line = v1 + slope * (pos15 - i1)
            live = good & (pos15 - i1 <= 3 * (i1 - i0))
            above = (c5 - line) * s > 0
            tl[s] = (live & above & ~np.roll(above, 1) & np.isfinite(np.roll(line, 1)), v0, i0, i1, slope)
            d5[s] = (dw == s) & (np.roll(dw, 1) != s)
        # ---------- TREND axis
        for s in (1, -1):
            m, v0, i0, i1, slope = tl[s]
            m = m & ok5 & (ctx[('TR2', s)] & m15tr[s])[p]
            I = np.where(m)[0]; I = I[I + 1 < N]
            if not len(I): continue
            P = p[I]; st_i = rs[P]; I0 = i0[I].astype(int)
            ext0 = np.array([(l15[a_:b_ + 1].min() if s == 1 else h15[a_:b_ + 1].max()) if b_ >= a_ else np.nan for a_, b_ in zip(st_i, I0)])
            imp = (v0[I] - ext0) * s
            pullx = np.array([(l15[b_:q + 1].min() if s == 1 else h15[b_:q + 1].max()) for b_, q in zip(I0, P)])
            depth = (v0[I] - pullx) * s / imp
            feat = dict(ep=ep[P], age=(P - st_i) / 4.0, imp=imp / H1A[I], depth=depth, span=i1[I] - i0[I], plen=P - I0,
                        steep=abs(slope[I]) / A15[I], h1sl=f.h1sl.to_numpy()[P] * s, op4=f.op4.to_numpy()[P] * s, sl4=f.sl4.to_numpy()[P] * s,
                        m20d=(c5[I] - f.h1m20.to_numpy()[P]) * s / H1A[I], er=f.h1er.to_numpy()[P])
            for stn, kk in (('A3', 3.0), ('A4', 4.0)):
                st = c5[I] - kk * A15[I] * s; nan = np.full(len(I), np.nan); SD = np.full(len(I), s, np.int64)
                for mn, swh, swl, arm, mb in (('T5a15_24', sh5, sl5, 1.5, 288), ('T5a15_72', sh5, sl5, 1.5, 864),
                                              ('T15a1_72', sh15m, sl15m, 1.0, 864), ('TBa1_120', bhm, blm, 1.0, 1440)):
                    R, X = run(I + 1, SD, st, nan, o5, h5, l5, c5, swh, swl, gap5, mb, arm, True)
                    rows.append(pd.DataFrame(dict(axis='trend', sym=sym, cfg=f'TL|{stn}|{mn}', t=t5[I], side=s, R0=R, cR=COST[sym] / ((o5[I + 1] - st) * s),
                                                  hours=(X - I - 1) / 12.0, **feat)))
        # ---------- RANGE axis
        side_d = f.side.to_numpy()[p]
        flat = (np.abs(f.sl4.to_numpy()[p]) < 0.15) & (f.h1er.to_numpy()[p] < 0.15)
        for s in (1, -1):
            zone = (rng_pos < 0.35) if s == 1 else (rng_pos > 0.65)
            for tg, trig in (('TL', tl[s][0]), ('D5', d5[s])):
                m = trig & ok5 & flat & (side_d == s) & zone
                I = np.where(m)[0]; I = I[I + 1 < N]
                if not len(I): continue
                SD = np.full(len(I), s, np.int64)
                st = np.where(s == 1, LO[I], HI[I]) - 0.3 * H1A[I] * s
                feat = dict(rpos=np.where(s == 1, rng_pos[I], 1 - rng_pos[I]), width=(HI[I] - LO[I]) / H1A[I], sl4=f.sl4.to_numpy()[p[I]] * s,
                            h1sl=f.h1sl.to_numpy()[p[I]] * s, op4=f.op4.to_numpy()[p[I]] * s, er=f.h1er.to_numpy()[p[I]])
                mid = (HI[I] + LO[I]) / 2; far = np.where(s == 1, LO[I] + 0.95 * (HI[I] - LO[I]), HI[I] - 0.95 * (HI[I] - LO[I]))
                nan = np.full(len(I), np.nan)
                for mn, tgt, arm, trl in (('mid', mid, 0, False), ('far', far, 0, False), ('T5a1', nan, 1.0, True), ('farT', far, 1.0, True)):
                    R, X = run(I + 1, SD, st, tgt, o5, h5, l5, c5, sh5, sl5, gap5, 864, arm, trl)
                    rows.append(pd.DataFrame(dict(axis='range', sym=sym, cfg=f'{tg}|{mn}', t=t5[I], side=s, R0=R, cR=COST[sym] / ((o5[I + 1] - st) * s),
                                                  hours=(X - I - 1) / 12.0, **feat)))
        print(sym, flush=True)
    d = pd.concat(rows, ignore_index=True); d = d[np.isfinite(d.R0)]
    d['R'] = d.R0 - d.cR; d['half'] = np.where(d.t < d.sym.map(lambda s: pd.Timestamp(SPLIT[s])), 1, 2)
    d.to_pickle('/home/user/trendlab/st/r7.pkl')

if __name__ == '__main__': main()
