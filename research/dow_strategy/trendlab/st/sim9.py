"""Range axis v2 (2026-11): R's idea (H4 range, trade only with the H1 trend) + what the short-term study found.

Context (side s, at the M5 bar's close): H4 range score RS > rs_min (live env.Env._range_score) and H4 close within 3 ATR(H4)
beyond its SMA200 on the trade side (R's 'sh < 3'), H1 SMA20/75 regime = s.
Triggers (M5 close): TL = M15 counter line break (round 6); ST = M15 stochastic 20 -> K over D -> over 20 completed on the last
closed M15 bar (engine order, sells mirrored); MA = M15 SMA20 touch closing back on the side (round 1 'MA', on the last M15 bar).
Features kept for narrowing: pullback number in the H1 regime (ep), pullback depth / impulse, RS, sh, daily side, H4 range position.
Stops: A3 = 3 ATR15; S200 = M15 SMA200 -/+ 10 pips (min 10 pips), like R. Exits: M5 trail from +1.5R up to 72h; bigger M15 swings
(ZigZag 6 x ATR7) from +1R up to 120h; target the far side of the 50-bar H4 range (stop as given), up to 120h.
"""
import sys, numpy as np, pandas as pd
from sim import COST, SPLIT, build
from sim5 import zig
from sim6 import zigx
from sim7 import run, atr7, zig3


def range_score(h4c, A):
    c = pd.Series(h4c); s75 = c.rolling(75).mean()
    absdev = (np.abs(c - s75) / pd.Series(A)).to_numpy(); slope = (np.abs(s75 - s75.shift(10)) / pd.Series(A)).to_numpy()
    er50 = (c.diff(50).abs() / c.diff().abs().rolling(50).sum()).to_numpy()
    parts = [1 - pd.Series(v).rolling(3000, min_periods=1500).rank(pct=True).to_numpy() for v in (absdev, slope, er50)]
    with np.errstate(all='ignore'):
        return np.nanmean(np.vstack(parts), axis=0)


def main(sym):
    rows = []
    f, ok, gap15, ctx, trg = build(sym); n = len(f)
    c = f.c.to_numpy(); m20 = f.m20.to_numpy(); a = f.a15.to_numpy(); h15, l15 = f.h.to_numpy(), f.l.to_numpy()
    m200 = pd.Series(c).rolling(200).mean().to_numpy()
    reg = np.sign(f.h1m20 - f.h1m75).fillna(0).to_numpy()
    ep = np.zeros(n); rs_i = np.zeros(n, np.int64); cur = 0; k = 0; armed = False; start = 0
    for i in range(1, n):
        if reg[i] != cur: cur = reg[i]; k = 0; armed = True; start = i
        if cur != 0:
            if (c[i] - m20[i]) * cur >= 2 * a[i]: armed = True
            if armed and trg[('MA', int(cur))][i]: k += 1; armed = False
        ep[i] = k; rs_i[i] = start
    # H4: range score (EWM ATR7 like env), SMA200, SMA1200, 50-bar range
    d = f.set_index('time')[['o', 'h', 'l', 'c']]
    h4 = d.resample('4h', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna()
    pc = h4.c.shift(); tr = np.maximum(h4.h - h4.l, np.maximum((h4.h - pc).abs(), (h4.l - pc).abs())); tr.iloc[0] = h4.h.iloc[0] - h4.l.iloc[0]
    A4 = tr.ewm(alpha=1 / 7, adjust=False).mean().to_numpy(); C4v = h4.c.to_numpy()
    RS = range_score(C4v, A4); S200 = pd.Series(C4v).rolling(200).mean().to_numpy(); S1200 = pd.Series(C4v).rolling(1200).mean().to_numpy()
    hi50 = h4.h.rolling(50).max().to_numpy(); lo50 = h4.l.rolling(50).min().to_numpy(); cl4 = (h4.index + pd.Timedelta('4h')).to_numpy()
    # M15 swings / lines, M5 data
    a7 = atr7(h15, l15, c); ZH, ZL = zigx(h15, l15, a7); bh, bl = zig3(h15, l15, a7, 6.0)
    m5 = pd.read_pickle(f'/home/user/trendlab/st/m5/m5_{sym}.pkl').reset_index(drop=True)
    t5 = m5.time.to_numpy(); o5, h5, l5, c5 = (m5[x].to_numpy(float) for x in ('open', 'high', 'low', 'close')); N = len(t5)
    sh5, sl5 = zig(h5, l5, atr7(h5, l5, c5))
    gap5 = np.r_[False, np.diff(t5).astype('timedelta64[m]').astype(int) > 180]
    ct15 = (f.time + pd.Timedelta('15min')).to_numpy(); ct5 = t5 + np.timedelta64(5, 'm')
    p = np.searchsorted(ct15, ct5, side='right') - 1; okp = p >= 0; p = np.maximum(p, 0)
    last15 = okp & (ct15[p] == ct5)                                  # this M5 bar closes the M15 bar p
    hr5 = pd.DatetimeIndex(t5).hour.to_numpy(); ok5 = okp & ok[p] & ~np.isin(hr5, (20, 21, 22))
    k4 = np.searchsorted(cl4, ct5, side='right') - 1; k4c = np.maximum(k4, 0)
    A15 = a[p]; bhm, blm = bh[p], bl[p]
    pos15 = p + ((t5 - f.time.to_numpy()[p]).astype('timedelta64[m]').astype(float) / 15.0)
    # stochastic sequence completion on M15 (engine order)
    K, D = f.K.to_numpy(), f.D.to_numpy(); done = {1: np.zeros(n, bool), -1: np.zeros(n, bool)}; st_ = {1: 0, -1: 0}
    for i in range(1, n):
        if not (np.isfinite(K[i]) and np.isfinite(D[i])): continue
        if st_[1] == 0 and K[i] < 20: st_[1] = 1
        elif st_[1] == 1 and K[i - 1] <= D[i - 1] and K[i] > D[i]: st_[1] = 2
        elif st_[1] == 2 and K[i - 1] <= 20 and K[i] > 20: st_[1] = 0; done[1][i] = True
        if st_[-1] == 0 and K[i] > 80: st_[-1] = 1
        elif st_[-1] == 1 and K[i - 1] >= D[i - 1] and K[i] < D[i]: st_[-1] = 2
        elif st_[-1] == 2 and K[i - 1] >= 80 and K[i] < 80: st_[-1] = 0; done[-1][i] = True
    pip = 0.01 if sym == 'USDJPY' else 1e-4
    for s in (1, -1):
        ctxs = (RS[k4c] > 0.7) & (k4 >= 0) & ((C4v[k4c] - S200[k4c]) * s / A4[k4c] < 3) & (reg[p] == s) & ok5
        Z = ZH if s == 1 else ZL
        v1, i1, v0, i0 = Z[p, 0], Z[p, 1], Z[p, 2], Z[p, 3]
        good = np.isfinite(v0) & ((v1 - v0) * s < 0) & (i1 > i0)
        line = v1 + (v1 - v0) / np.where(good, i1 - i0, 1) * (pos15 - i1); live = good & (pos15 - i1 <= 3 * (i1 - i0))
        above = (c5 - line) * s > 0
        trig = {'TL': live & above & ~np.roll(above, 1) & np.isfinite(np.roll(line, 1)),
                'ST': last15 & done[s][p], 'MA': last15 & trg[('MA', s)][p]}
        for tg, tm in trig.items():
            I = np.where(tm & ctxs)[0]; I = I[I + 1 < N]
            if not len(I): continue
            P = p[I]; sti = rs_i[P]
            ext0 = np.array([(l15[a_:b_ + 1].min() if s == 1 else h15[a_:b_ + 1].max()) for a_, b_ in zip(sti, P)])
            ext1 = np.array([(h15[a_:b_ + 1].max() if s == 1 else l15[a_:b_ + 1].min()) for a_, b_ in zip(sti, P)])
            imp = (ext1 - ext0) * s; depth = np.where(imp > 0, (ext1 - c5[I]) * s / np.where(imp > 0, imp, 1), np.nan)
            kk = k4c[I]
            feat = dict(ep=ep[P], depth=depth, rs=RS[kk], sh=(C4v[kk] - S200[kk]) * s / A4[kk], sd=(C4v[kk] - S1200[kk]) * s / A4[kk],
                        rpos=np.where(s == 1, (c5[I] - lo50[kk]) / (hi50[kk] - lo50[kk]), (hi50[kk] - c5[I]) / (hi50[kk] - lo50[kk])),
                        rw=(hi50[kk] - lo50[kk]) / A4[kk])
            SD = np.full(len(I), s, np.int64); nan = np.full(len(I), np.nan)
            stops = {'A3': c5[I] - 3 * A15[I] * s,
                     'S200': np.where(s == 1, np.minimum(m200[P] - 10 * pip, c5[I] - 10 * pip), np.maximum(m200[P] + 10 * pip, c5[I] + 10 * pip))}
            far = np.where(s == 1, hi50[kk], lo50[kk])
            for stn, st in stops.items():
                for mn, tgt, swh, swl, arm, mb, trl in (('M5a15_72', nan, sh5, sl5, 1.5, 864, True), ('BIGa1_120', nan, bhm, blm, 1.0, 1440, True),
                                                        ('FAR_120', far, sh5, sl5, 0, 1440, False)):
                    R, X = run(I + 1, SD, st, tgt, o5, h5, l5, c5, swh, swl, gap5, mb, arm, trl)
                    rows.append(pd.DataFrame(dict(sym=sym, cfg=f'{tg}|{stn}|{mn}', t=t5[I], side=s, R0=R, cR=COST[sym] / ((o5[I + 1] - st) * s),
                                                  hours=(X - I - 1) / 12.0, **feat)))
    out = pd.concat(rows, ignore_index=True); out = out[np.isfinite(out.R0)]
    out['R'] = out.R0 - out.cR; out['half'] = np.where(out.t < pd.Timestamp(SPLIT[sym]), 1, 2)
    out.to_pickle(f'/home/user/trendlab/st/r9_{sym}.pkl'); print(sym, len(out), flush=True)


if __name__ == '__main__':
    main(sys.argv[1])
