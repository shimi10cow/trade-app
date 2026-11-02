"""Short-term study, round 1: contexts x M15 triggers x stops x exits on the 6 main instruments, all exits within 24h.

Entry at the next M15 open after the signal bar. One position per (instrument, config) at a time.
Contexts: TR = H1 SMA20/75 and MA75 slope with the side + daily side (H4 SMA1200); TR2 = TR + H4 opening*side < 2.5;
          RG = H1 range (ER48 < 0.10, |MA75 slope| < 0.3 ATR); RGL = RG and price in the lower / upper third of the 48-bar H1 range.
Triggers: ST = stochastic K crosses D from below 20 / above 80; DW = M15 dow turns to the side; MA = M15 bar dips to SMA20 and closes
          back on the side with the M15 SMA20/75 on the side.
Stops: SW = last confirmed M15 swing (+0.1 ATR15), 0.5..6 ATR15 wide, else skipped; AT = 1.5 ATR15.
Exits: T24 / T8 = from +1R trail the stop to confirmed M15 swings, close after 24h / 8h; MA = close on an M15 close through SMA20;
       TG = take profit at the H1 48-bar range middle (range contexts only). All close before a gap of 3h+ (weekend).
"""
import sys, numpy as np, pandas as pd, numba as nb
COST = {'EURUSD': 1.2e-4, 'USDJPY': 1.5e-2, 'XAUUSD': 2.5e-4, 'US30': 1.5e-4, 'US500': 2e-4, 'JP225': 3e-4}
SPLIT = {'EURUSD': '2016', 'USDJPY': '2016', 'XAUUSD': '2016', 'US30': '2020-07', 'US500': '2021-10', 'JP225': '2021-10'}
BADH = {k: (20, 21, 22) for k in ('EURUSD', 'USDJPY', 'XAUUSD')} | {k: (23, 0, 1) for k in ('US30', 'US500', 'JP225')}

@nb.njit(cache=True)
def run(sig, side, stop, tgt, o, h, l, c, sh, sl, m20, gap, maxb, mode, a15):
    # mode 0 = trail swings from +1R, 1 = MA20 close exit, 2 = target
    n = len(o); out_i = np.full(len(sig), -1); out_R = np.zeros(len(sig)); out_x = np.zeros(len(sig), np.int64); busy = -1
    for k in range(len(sig)):
        i = sig[k]
        if i <= busy or i + 1 >= n: continue
        s = side[k]; en = o[i + 1]; st = stop[k]; risk = (en - st) * s
        if risk <= 0.3 * a15[i]: continue
        tp = tgt[k]
        if mode == 2 and (tp - en) * s <= 0: continue
        ex = np.nan; j = i + 1; armed = False
        while True:
            if s == 1:
                if l[j] <= st: ex = min(st, o[j]); break
                if mode == 2 and h[j] >= tp: ex = max(tp, o[j]); break
            else:
                if h[j] >= st: ex = max(st, o[j]); break
                if mode == 2 and l[j] <= tp: ex = min(tp, o[j]); break
            if mode == 1 and (c[j] - m20[j]) * s < 0: ex = c[j]; break
            if j - i >= maxb or j + 1 >= n or gap[j + 1]: ex = c[j]; break
            if mode == 0:
                if not armed and ((h[j] if s == 1 else l[j]) - en) * s >= risk: armed = True
                if armed:
                    nsw = (sl[j] if s == 1 else sh[j])
                    if np.isfinite(nsw) and (nsw - st) * s > 0 and (c[j] - nsw) * s > 0: st = nsw
            j += 1
        out_i[k] = i; out_R[k] = (ex - en) * s / risk; out_x[k] = j; busy = j
    return out_i, out_R, out_x

def build(sym):
    f = pd.read_pickle(f'/home/user/trendlab/st/f_{sym}.pkl')
    hr = f.time.dt.hour.to_numpy(); ok = ~np.isin(hr, BADH[sym])
    gap = (f.time.diff().dt.total_seconds().fillna(0) > 3 * 3600).to_numpy()
    K, D = f.K.to_numpy(), f.D.to_numpy(); Kp, Dp = np.roll(K, 1), np.roll(D, 1)
    dw = f.dow15.to_numpy(); dwp = np.roll(dw, 1)
    pos = ((f.c - f.h1lo) / (f.h1hi - f.h1lo)).to_numpy()
    ctx, trg = {}, {}
    for s in (1, -1):
        tr = ((f.h1m20 - f.h1m75) * s > 0) & (f.h1sl * s > 0) & (f.side == s)
        ctx[('TR', s)] = tr.to_numpy()
        ctx[('TR2', s)] = (tr & (f.op4 * s < 2.5)).to_numpy()
        rg = ((f.h1er < 0.10) & (f.h1sl.abs() < 0.3)).to_numpy()
        ctx[('RG', s)] = rg
        ctx[('RGL', s)] = rg & ((pos < 0.34) if s == 1 else (pos > 0.66))
        if s == 1: trg[('ST', s)] = (Kp < Dp) & (K >= D) & (Kp < 20)
        else: trg[('ST', s)] = (Kp > Dp) & (K <= D) & (Kp > 80)
        trg[('DW', s)] = (dw == s) & (dwp != s)
        m20, m75 = f.m20.to_numpy(), f.m75.to_numpy()
        if s == 1: trg[('MA', s)] = (f.l.to_numpy() <= m20) & (f.c.to_numpy() > m20) & (m20 > m75) & (f.c.to_numpy() > f.o.to_numpy())
        else: trg[('MA', s)] = (f.h.to_numpy() >= m20) & (f.c.to_numpy() < m20) & (m20 < m75) & (f.c.to_numpy() < f.o.to_numpy())
    return f, ok, gap, ctx, trg

def main(sym):
    f, ok, gap, ctx, trg = build(sym)
    A = {k: f[k].to_numpy(float) for k in ('o', 'h', 'l', 'c', 'sh', 'sl', 'm20', 'a15')}
    mid = ((f.h1hi + f.h1lo) / 2).to_numpy()
    res = []
    for cx in ('TR', 'TR2', 'RG', 'RGL'):
        for tg in ('ST', 'DW', 'MA'):
            idx, sd = [], []
            for s in (1, -1):
                w = np.where(ctx[(cx, s)] & trg[(tg, s)] & ok)[0]; idx.append(w); sd.append(np.full(len(w), s))
            idx = np.concatenate(idx); sd = np.concatenate(sd); o_ = np.argsort(idx, kind='stable'); idx, sd = idx[o_], sd[o_]
            for stn in ('SW', 'AT'):
                if stn == 'SW':
                    swv = np.where(sd == 1, A['sl'][idx], A['sh'][idx]); st = swv - 0.1 * A['a15'][idx] * sd
                    wid = (A['c'][idx] - st) * sd / A['a15'][idx]; keep = np.isfinite(st) & (wid >= 0.5) & (wid <= 6)
                else:
                    st = A['c'][idx] - 1.5 * A['a15'][idx] * sd; keep = np.ones(len(idx), bool)
                ii, ss, st2 = idx[keep], sd[keep].astype(np.int64), st[keep]
                exits = [('T24', 0, 96), ('T8', 0, 32), ('MA', 1, 96)] + ([('TG', 2, 96)] if cx.startswith('RG') else [])
                for xn, mode, mb in exits:
                    oi, R, ox = run(ii, ss, st2, mid[ii], A['o'], A['h'], A['l'], A['c'], A['sh'], A['sl'], A['m20'], gap, mb, mode, A['a15'])
                    sel = oi >= 0
                    if not sel.any(): continue
                    en = A['o'][oi[sel] + 1]; risk = (en - st2[sel]) * ss[sel]
                    res.append(pd.DataFrame(dict(sym=sym, cfg=f'{cx}|{tg}|{stn}|{xn}', t=f.time.to_numpy()[oi[sel]], side=ss[sel],
                                                 R0=R[sel], cR=COST[sym] / risk, bars=ox[sel] - oi[sel])))
    out = pd.concat(res, ignore_index=True); out['half'] = np.where(out.t < pd.Timestamp(SPLIT[sym]), 1, 2)
    out.to_pickle(f'/home/user/trendlab/st/r1_{sym}.pkl'); print(sym, len(out), flush=True)

if __name__ == '__main__': main(sys.argv[1])
