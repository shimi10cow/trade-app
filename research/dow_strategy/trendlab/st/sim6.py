"""Round 6 (EURUSD / XAUUSD): M5 entries in the trend, only early in the M15 push (before the correction), M5 trail from +1R.

Context (side s, known at the M5 bar's close):
  TR  = TR2 (H1 SMA20/75 + MA75 slope + daily side + H4 opening < 2.5) and the M15 trend on the side (SMA20 vs 75 and M15 dow);
  RG  = H1 range (ER48 < 0.10, |MA75 slope| < 0.3) and the daily side = s (range, but only the long-term direction).
  ep  = M15 pullback number in the H1 regime (round 4 count, away 2 ATR15): all / <= 2.
Triggers on the M5 close:
  TL  = M5 close breaks the M15 counter line (through the last two confirmed M15 swing highs, the 2nd lower; mirrored for sells),
        within 3x the line's span after its 2nd point;
  D5  = M5 dow turns to the side, after price touched the M15 SMA20 in the last 12 M5 bars;
  K5  = M5 stochastic (14,3,3) K crosses D from < 20 (> 80), same touch condition.
Stop: P = the pullback extreme (lowest low of the last 24 M5 bars) - 0.1 ATR15, at least 1.0 ATR15 wide; A3 = 3 ATR15.
Exit: trail M5 swings from +1R / +1.5R (T5a1 / T5a15), M15 swings from +1R (T15a1), or 24h only. All close after 24h.
"""
import numpy as np, pandas as pd, numba as nb
from sim import COST, SPLIT, build
from sim5 import zig, run

@nb.njit(cache=True)
def zigx(h, l, a7):
    n = len(h); out = np.full((n, 4), np.nan)        # last high value, its bar, previous high value, its bar  (and lows below)
    outl = np.full((n, 4), np.nan); d = 1; ext = h[0]; ei = 0
    H = np.array([np.nan, np.nan, np.nan, np.nan]); L = np.array([np.nan, np.nan, np.nan, np.nan])
    for i in range(1, n):
        th = 1.9 * a7[i]
        if d == 1:
            if h[i] >= ext: ext = h[i]; ei = i
            elif l[i] <= ext - th:
                H[2] = H[0]; H[3] = H[1]; H[0] = ext; H[1] = ei; d = -1; ext = l[i]; ei = i
        else:
            if l[i] <= ext: ext = l[i]; ei = i
            elif h[i] >= ext + th:
                L[2] = L[0]; L[3] = L[1]; L[0] = ext; L[1] = ei; d = 1; ext = h[i]; ei = i
        out[i] = H; outl[i] = L
    return out, outl

def main():
    rows = []
    for sym in ('EURUSD', 'XAUUSD'):
        f, ok, gap15, ctx, trg = build(sym); n = len(f)
        c = f.c.to_numpy(); m20 = f.m20.to_numpy(); m75 = f.m75.to_numpy(); a = f.a15.to_numpy()
        reg = np.sign(f.h1m20 - f.h1m75).fillna(0).to_numpy()
        ep = np.zeros(n); cur = 0; k = 0; armed = False
        for i in range(1, n):
            if reg[i] != cur: cur = reg[i]; k = 0; armed = True
            if cur != 0:
                if (c[i] - m20[i]) * cur >= 2 * a[i]: armed = True
                if armed and trg[('MA', int(cur))][i]: k += 1; armed = False
            ep[i] = k
        h15, l15 = f.h.to_numpy(), f.l.to_numpy()
        pc = np.r_[c[0], c[:-1]]; a7 = pd.Series(np.maximum(h15 - l15, np.maximum(abs(h15 - pc), abs(l15 - pc)))).ewm(alpha=1 / 7, adjust=False).mean().to_numpy()
        ZH, ZL = zigx(h15, l15, a7)
        ctxM = {}
        for s in (1, -1):
            m15tr = ((m20 - m75) * s > 0) & (f.dow15.to_numpy() == s)
            ctxM[('TR', s)] = ctx[('TR2', s)] & m15tr
            ctxM[('RG', s)] = ctx[('RG', s)] & (f.side.to_numpy() == s)
        # ---- M5 arrays and M15 values mapped by availability (M15 close <= M5 close)
        m5 = pd.read_pickle(f'/home/user/trendlab/st/m5/m5_{sym}.pkl').reset_index(drop=True)
        t5 = m5.time.to_numpy(); o5, h5, l5, c5 = (m5[x].to_numpy(float) for x in ('open', 'high', 'low', 'close')); N = len(t5)
        pc5 = np.r_[c5[0], c5[:-1]]; a75 = pd.Series(np.maximum(h5 - l5, np.maximum(abs(h5 - pc5), abs(l5 - pc5)))).ewm(alpha=1 / 7, adjust=False).mean().to_numpy()
        sh5, sl5 = zig(h5, l5, a75)
        gap5 = np.r_[False, np.diff(t5).astype('timedelta64[m]').astype(int) > 180]
        ct15 = (f.time + pd.Timedelta('15min')).to_numpy(); p = np.searchsorted(ct15, t5 + np.timedelta64(5, 'm'), side='right') - 1
        okp = p >= 0; p = np.maximum(p, 0)
        hr5 = pd.DatetimeIndex(t5).hour.to_numpy(); ok5 = okp & ok[p] & ~np.isin(hr5, (20, 21, 22))
        A15 = a[p]; M20 = m20[p]
        # M5 dow and stochastic
        dw = np.zeros(N); d = 0
        for i in range(1, N):
            if np.isfinite(sh5[i - 1]) and c5[i] > sh5[i - 1]: d = 1
            elif np.isfinite(sl5[i - 1]) and c5[i] < sl5[i - 1]: d = -1
            dw[i] = d
        S = pd.Series; lo14 = S(l5).rolling(14).min(); hi14 = S(h5).rolling(14).max()
        K = (100 * (S(c5) - lo14) / (hi14 - lo14).replace(0, np.nan)).rolling(3).mean(); D = K.rolling(3).mean()
        K, D = K.to_numpy(), D.to_numpy(); Kp, Dp = np.roll(K, 1), np.roll(D, 1)
        lo24 = S(l5).rolling(24).min().to_numpy(); hi24 = S(h5).rolling(24).max().to_numpy()
        touch = {1: S(l5 <= M20).rolling(12).max().to_numpy() > 0, -1: S(h5 >= M20).rolling(12).max().to_numpy() > 0}
        # M15 counter line projected to the M5 bar (bar units: M15 index; M5 position in M15 units = p + fraction)
        pos15 = p + ((t5 - f.time.to_numpy()[p]).astype('timedelta64[m]').astype(float) / 15.0)
        trig = {}
        for s in (1, -1):
            Z = ZH if s == 1 else ZL                          # buys break a falling line of highs; sells a rising line of lows
            v1, i1, v0, i0 = Z[p, 0], Z[p, 1], Z[p, 2], Z[p, 3]
            good = np.isfinite(v0) & ((v1 - v0) * s < 0) & (i1 > i0)
            slope = (v1 - v0) / np.where(good, i1 - i0, 1)
            line = v1 + slope * (pos15 - i1)
            live = good & (pos15 - i1 <= 3 * (i1 - i0))
            above = (c5 - line) * s > 0; abovep = np.roll(above, 1); linep = np.roll(line, 1)
            trig[('TL', s)] = live & above & ~abovep & np.isfinite(linep)
            trig[('D5', s)] = (dw == s) & (np.roll(dw, 1) != s) & touch[s]
            if s == 1: trig[('K5', s)] = (Kp < Dp) & (K >= D) & (Kp < 20) & touch[s]
            else: trig[('K5', s)] = (Kp > Dp) & (K <= D) & (Kp > 80) & touch[s]
        for cx in ('TR', 'RG'):
            for tg in ('TL', 'D5', 'K5'):
                for epn, epm in (('all', 99), ('ep2', 2)):
                    I, SD = [], []
                    for s in (1, -1):
                        m = trig[(tg, s)] & ctxM[(cx, s)][p] & ok5
                        if cx == 'TR': m &= (ep[p] <= epm)
                        elif epn == 'ep2': continue
                        w = np.where(m)[0]; I.append(w); SD.append(np.full(len(w), s))
                    if not I: continue
                    I = np.concatenate(I); SD = np.concatenate(SD).astype(np.int64); q = np.argsort(I, kind='stable'); I, SD = I[q], SD[q]
                    I = I[I + 1 < N]; SD = SD[:len(I)]
                    if len(I) == 0: continue
                    ext = np.where(SD == 1, lo24[I], hi24[I])
                    stP = ext - 0.1 * A15[I] * SD
                    stP = np.where((c5[I] - stP) * SD < 1.0 * A15[I], c5[I] - 1.0 * A15[I] * SD, stP)
                    for stn, st in (('P', stP), ('A3', c5[I] - 3 * A15[I] * SD)):
                        for mn, swh, swl, arm, trl in (('T5a1', sh5, sl5, 1.0, True), ('T5a15', sh5, sl5, 1.5, True), ('time', sh5, sl5, 0, False)):
                            R, X = run(I + 1, SD, st, o5, h5, l5, c5, swh, swl, gap5, 288, arm, False, trl)
                            g = np.isfinite(R); en = o5[I + 1][g]; risk = (en - st[g]) * SD[g]; tt = t5[I][g]
                            rows.append(pd.DataFrame(dict(sym=sym, cfg=f'{cx}|{tg}|{epn}|{stn}|{mn}', t=tt, side=SD[g], R0=R[g], cR=COST[sym] / risk,
                                                          mins=(X[g] - I[g] - 1) * 5, wid=risk / A15[I][g],
                                                          half=np.where(tt < np.datetime64(pd.Timestamp(SPLIT[sym])), 1, 2))))
        print(sym, flush=True)
    d = pd.concat(rows, ignore_index=True); d['R'] = d.R0 - d.cR; d.to_pickle('/home/user/trendlab/st/r6.pkl')

if __name__ == '__main__': main()
