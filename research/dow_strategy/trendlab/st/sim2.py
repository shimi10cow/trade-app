"""Short-term study, round 2: mean reversion to the M15 SMA20 (the intraday analogue of the daily RSI(2) EAs).

Signal (buy; sell mirrored) on an M15 close: stretched below the M15 SMA20 by k ATR15 (S15 / S25), or slow K < 10 below the SMA20
(K10, first bar), or the stochastic turning up from < 20 while stretched 1 ATR15+ (KT).
Contexts: TR / TR2 / RG as round 1, NO = none, CT = against TR (fading the trend, for comparison).
Stop: 2 or 3 ATR15 from the entry. Exit: an M15 close back through the SMA20 (the mean), the stop, 24h (or 8h), or before a 3h gap.
"""
import sys, numpy as np, pandas as pd, numba as nb
from sim import COST, SPLIT, BADH, build

@nb.njit(cache=True)
def run(sig, side, stop, o, h, l, c, m20, gap, maxb, a15):
    n = len(o); out_i = np.full(len(sig), -1); out_R = np.zeros(len(sig)); out_x = np.zeros(len(sig), np.int64); busy = -1
    for k in range(len(sig)):
        i = sig[k]
        if i <= busy or i + 1 >= n: continue
        s = side[k]; en = o[i + 1]; st = stop[k]; risk = (en - st) * s
        if risk <= 0: continue
        j = i + 1; ex = np.nan
        while True:
            if s == 1 and l[j] <= st: ex = min(st, o[j]); break
            if s == -1 and h[j] >= st: ex = max(st, o[j]); break
            if (c[j] - m20[j]) * s >= 0: ex = c[j]; break
            if j - i >= maxb or j + 1 >= n or gap[j + 1]: ex = c[j]; break
            j += 1
        out_i[k] = i; out_R[k] = (ex - en) * s / risk; out_x[k] = j; busy = j
    return out_i, out_R, out_x

def main(sym):
    f, ok, gap, ctx, _ = build(sym)
    A = {k: f[k].to_numpy(float) for k in ('o', 'h', 'l', 'c', 'm20', 'a15', 'K', 'D')}
    Kp, Dp = np.roll(A['K'], 1), np.roll(A['D'], 1)
    z = (A['c'] - A['m20']) / A['a15']
    trg = {}
    for s in (1, -1):
        zs = z * s
        trg[('S15', s)] = (zs < -1.5) & (np.roll(zs, 1) >= -1.5)
        trg[('S25', s)] = (zs < -2.5) & (np.roll(zs, 1) >= -2.5)
        Ks = A['K'] if s == 1 else 100 - A['K']; Kps = np.roll(Ks, 1)
        trg[('K10', s)] = (Ks < 10) & (Kps >= 10) & (zs < 0)
        cross = (Kp < Dp) & (A['K'] >= A['D']) if s == 1 else (Kp > Dp) & (A['K'] <= A['D'])
        trg[('KT', s)] = cross & (Kps < 20) & (zs < -1.0)
    for s in (1, -1):
        ctx[('NO', s)] = np.ones(len(f), bool); ctx[('CT', s)] = ctx[('TR', -s)]
    res = []
    for cx in ('TR', 'TR2', 'RG', 'NO', 'CT'):
        for tg in ('S15', 'S25', 'K10', 'KT'):
            idx = np.concatenate([np.where(ctx[(cx, s)] & trg[(tg, s)] & ok)[0] for s in (1, -1)])
            sd = np.concatenate([np.full((ctx[(cx, s)] & trg[(tg, s)] & ok).sum(), s) for s in (1, -1)])
            o_ = np.argsort(idx, kind='stable'); idx, sd = idx[o_], sd[o_].astype(np.int64)
            for kst in (2.0, 3.0):
                st = A['c'][idx] - kst * A['a15'][idx] * sd
                for xn, mb in (('24', 96), ('8', 32)):
                    oi, R, ox = run(idx, sd, st, A['o'], A['h'], A['l'], A['c'], A['m20'], gap, mb, A['a15'])
                    sel = oi >= 0; en = A['o'][oi[sel] + 1]; risk = (en - st[sel]) * sd[sel]
                    res.append(pd.DataFrame(dict(sym=sym, cfg=f'{cx}|{tg}|AT{kst:g}|{xn}', t=f.time.to_numpy()[oi[sel]], side=sd[sel],
                                                 R0=R[sel], cR=COST[sym] / risk, bars=ox[sel] - oi[sel])))
    out = pd.concat(res, ignore_index=True); out['half'] = np.where(out.t < pd.Timestamp(SPLIT[sym]), 1, 2)
    out.to_pickle(f'/home/user/trendlab/st/r2_{sym}.pkl'); print(sym, len(out), flush=True)

if __name__ == '__main__': main(sys.argv[1])
