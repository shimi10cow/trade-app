"""Short-term study, round 3: trend-side M15 SMA20 pullback (TR2 + MA of round 1) with exits that leave room.

Entry: TR2 context (H1 SMA20/75 + MA75 slope + daily side + H4 opening < 2.5) and an M15 bar that dips to the SMA20 and closes back
on the side (bullish bar, M15 SMA20 above SMA75); next M15 open. Variants of the trigger: MAx = without the bullish-bar check.
Stop: k ATR15 (3 / 4 / 6) or below the M15 SMA75 by 1 ATR15 (M75). Exit: N hours (8 / 16 / 24), optionally earlier on an M15 close
through the SMA75 (X75), or trail M15 swings from +1R (TRL). Max open per instrument: 1 or 2.
"""
import sys, numpy as np, pandas as pd, numba as nb
from sim import COST, SPLIT, BADH, build

@nb.njit(cache=True)
def run(sig, side, stop, o, h, l, c, m75, sh, sl, gap, maxb, x75, trl, maxpos):
    n = len(o); out_i = np.full(len(sig), -1); out_R = np.zeros(len(sig)); out_x = np.zeros(len(sig), np.int64)
    ends = np.full(maxpos, -1)
    for k in range(len(sig)):
        i = sig[k]
        if i + 1 >= n: continue
        slot = -1
        for q in range(maxpos):
            if ends[q] < i: slot = q; break
        if slot < 0: continue
        s = side[k]; en = o[i + 1]; st = stop[k]; risk = (en - st) * s
        if risk <= 0: continue
        j = i + 1; ex = np.nan; armed = False
        while True:
            if s == 1 and l[j] <= st: ex = min(st, o[j]); break
            if s == -1 and h[j] >= st: ex = max(st, o[j]); break
            if x75 and (c[j] - m75[j]) * s < 0: ex = c[j]; break
            if j - i >= maxb or j + 1 >= n or gap[j + 1]: ex = c[j]; break
            if trl:
                if not armed and ((h[j] if s == 1 else l[j]) - en) * s >= risk: armed = True
                if armed:
                    nsw = sl[j] if s == 1 else sh[j]
                    if np.isfinite(nsw) and (nsw - st) * s > 0 and (c[j] - nsw) * s > 0: st = nsw
            j += 1
        out_i[k] = i; out_R[k] = (ex - en) * s / risk; out_x[k] = j; ends[slot] = j
    return out_i, out_R, out_x

def signals(sym, var='MA'):
    f, ok, gap, ctx, trg = build(sym)
    c, o, l, h, m20, m75 = (f[k].to_numpy() for k in ('c', 'o', 'l', 'h', 'm20', 'm75'))
    idx, sd = [], []
    for s in (1, -1):
        if var == 'MA': t = trg[('MA', s)]
        elif var == 'MAx': t = ((l <= m20) & (c > m20) & (m20 > m75)) if s == 1 else ((h >= m20) & (c < m20) & (m20 < m75))
        w = np.where(ctx[('TR2', s)] & t & ok)[0]; idx.append(w); sd.append(np.full(len(w), s))
    idx = np.concatenate(idx); sd = np.concatenate(sd).astype(np.int64); q = np.argsort(idx, kind='stable')
    return f, gap, idx[q], sd[q]

def main(sym):
    res = []
    for var in ('MA', 'MAx'):
        f, gap, idx, sd = signals(sym, var)
        A = {k: f[k].to_numpy(float) for k in ('o', 'h', 'l', 'c', 'm75', 'sh', 'sl', 'a15')}
        for stn in ('A3', 'A4', 'A6', 'M75'):
            st = (A['c'][idx] - float(stn[1:]) * A['a15'][idx] * sd) if stn[0] == 'A' else (A['m75'][idx] - A['a15'][idx] * sd)
            for hrs in (8, 16, 24):
                for xn, x75, trl in (('T', False, False), ('X75', True, False), ('TRL', False, True)):
                    for mp in (1, 2):
                        oi, R, ox = run(idx, sd, st, A['o'], A['h'], A['l'], A['c'], A['m75'], A['sh'], A['sl'], gap, hrs * 4, x75, trl, mp)
                        sel = oi >= 0; en = A['o'][oi[sel] + 1]; risk = (en - st[sel]) * sd[sel]
                        res.append(pd.DataFrame(dict(sym=sym, cfg=f'{var}|{stn}|{hrs}h|{xn}|p{mp}', t=f.time.to_numpy()[oi[sel]], side=sd[sel],
                                                     R0=R[sel], cR=COST[sym] / risk, bars=ox[sel] - oi[sel], ra=risk / A['a15'][oi[sel]])))
    out = pd.concat(res, ignore_index=True); out['half'] = np.where(out.t < pd.Timestamp(SPLIT[sym]), 1, 2)
    out.to_pickle(f'/home/user/trendlab/st/r3_{sym}.pkl'); print(sym, len(out), flush=True)

if __name__ == '__main__': main(sys.argv[1])
