"""Round 5 (EURUSD / XAUUSD): M15 entry, exits managed on M5.

Entries: the numbered trend-side pullbacks of round 4 (TR2 + M15 SMA20 touch, away 2 ATR15), pullbacks 1-5.
Simulated on M5 bars: entry at the M5 open right after the signal M15 bar closes.
Initial stop: S15 = last confirmed M15 swing -0.1 ATR15; S5 = last confirmed M5 swing -0.1 ATR15 (M5 ZigZag 1.9 x ATR7 on M5);
              A4 = 4 ATR15.
Management: trail the stop to confirmed swings of M5 (T5) or M15 (T15), starting once price has gone arm x R (0 / 0.5 / 1) in favour;
            'C' variants exit on an M5 close beyond the swing instead of a touch. Or none (time only). All exit after 24h or before a gap.
"""
import numpy as np, pandas as pd, numba as nb
from sim import COST, SPLIT, build

def zig(h, l, a7):
    n = len(h); sh = np.full(n, np.nan); sl = np.full(n, np.nan); d = 1; ext = h[0]; lh = np.nan; ll = np.nan
    for i in range(1, n):
        th = 1.9 * a7[i]
        if d == 1:
            if h[i] >= ext: ext = h[i]
            elif l[i] <= ext - th: lh = ext; d = -1; ext = l[i]
        else:
            if l[i] <= ext: ext = l[i]
            elif h[i] >= ext + th: ll = ext; d = 1; ext = h[i]
        sh[i] = lh; sl[i] = ll
    return sh, sl
zig = nb.njit(cache=True)(zig)

@nb.njit(cache=True)
def run(ent, side, stop, o, h, l, c, swh, swl, gap, maxb, arm, closex, trail):
    n = len(o); R = np.full(len(ent), np.nan); X = np.zeros(len(ent), np.int64); ends = np.full(2, -1)
    for k in range(len(ent)):
        e = ent[k]
        if e >= n: continue
        slot = -1
        for q in range(2):
            if ends[q] < e: slot = q; break
        if slot < 0: continue
        s = side[k]; en = o[e]; st = stop[k]; risk = (en - st) * s
        if risk <= 0: continue
        j = e; ex = np.nan; armed = arm <= 0; ts = st          # ts = trailing level (exit on close beyond it when closex)
        while True:
            if s == 1 and l[j] <= st: ex = min(st, o[j]); break
            if s == -1 and h[j] >= st: ex = max(st, o[j]); break
            if closex and armed and (c[j] - ts) * s < 0: ex = c[j]; break
            if j - e >= maxb or j + 1 >= n or gap[j + 1]: ex = c[j]; break
            if trail:
                if not armed and ((h[j] if s == 1 else l[j]) - en) * s >= arm * risk: armed = True
                if armed:
                    nsw = swl[j] if s == 1 else swh[j]
                    if np.isfinite(nsw) and (nsw - ts) * s > 0 and (c[j] - nsw) * s > 0:
                        ts = nsw
                        if not closex: st = nsw
            j += 1
        R[k] = (ex - en) * s / risk; X[k] = j; ends[slot] = j
    return R, X

def main():
    rows = []
    for sym in ('EURUSD', 'XAUUSD'):
        f, ok, gap15, ctx, trg = build(sym); n = len(f)
        c = f.c.to_numpy(); m20 = f.m20.to_numpy(); a = f.a15.to_numpy()
        reg = np.sign(f.h1m20 - f.h1m75).fillna(0).to_numpy()
        idx, sd, num = [], [], []; cur = 0; k = 0; armed = False
        for i in range(1, n):
            if reg[i] != cur: cur = reg[i]; k = 0; armed = True
            if cur == 0: continue
            if (c[i] - m20[i]) * cur >= 2 * a[i]: armed = True
            if armed and trg[('MA', int(cur))][i]:
                k += 1; armed = False
                if ctx[('TR2', int(cur))][i] and ok[i] and k <= 5: idx.append(i); sd.append(int(cur)); num.append(k)
        idx = np.array(idx); sd = np.array(sd, dtype=np.int64); num = np.array(num)
        m5 = pd.read_pickle(f'/home/user/trendlab/st/m5/m5_{sym}.pkl').reset_index(drop=True)
        t5 = m5.time.to_numpy(); o5, h5, l5, c5 = (m5[x].to_numpy(float) for x in ('open', 'high', 'low', 'close'))
        pc = np.r_[c5[0], c5[:-1]]; tr = np.maximum(h5 - l5, np.maximum(np.abs(h5 - pc), np.abs(l5 - pc)))
        a7 = pd.Series(tr).ewm(alpha=1 / 7, adjust=False).mean().to_numpy()
        sh5, sl5 = zig(h5, l5, a7)
        gap5 = np.r_[False, np.diff(t5).astype('timedelta64[m]').astype(int) > 180]
        # M15 swings known at the M15 close -> M5 bars whose close is at/after it
        ct15 = (f.time + pd.Timedelta('15min')).to_numpy(); ct5 = t5 + np.timedelta64(5, 'm')
        p = np.searchsorted(ct15, ct5, side='right') - 1
        sh15 = np.where(p >= 0, f.sh.to_numpy()[p], np.nan); sl15 = np.where(p >= 0, f.sl.to_numpy()[p], np.nan)
        ent = np.searchsorted(t5, ct15[idx])                  # first M5 bar opening at the signal bar's close
        okm = (ent < len(t5)) & (t5[np.minimum(ent, len(t5) - 1)] == ct15[idx]); idx, sd, num, ent = idx[okm], sd[okm], num[okm], ent[okm]
        e1 = ent - 1                                          # last M5 bar of the signal (closed) -> M5 swing known there
        aa = a[idx]
        stops = {'S15': np.where(sd == 1, f.sl.to_numpy()[idx], f.sh.to_numpy()[idx]) - 0.1 * aa * sd,
                 'S5': np.where(sd == 1, sl5[e1], sh5[e1]) - 0.1 * aa * sd,
                 'A4': c[idx] - 4 * aa * sd}
        for stn, st in stops.items():
            wid = (c[idx] - st) * sd / aa; keep = np.isfinite(st) & (wid >= 0.3) & (wid <= 8)
            for mn, swh, swl, arm, cx, trl in [('time', sh5, sl5, 0, False, False),
                                                ('T5a0', sh5, sl5, 0, False, True), ('T5a.5', sh5, sl5, .5, False, True), ('T5a1', sh5, sl5, 1, False, True),
                                                ('T5Ca0', sh5, sl5, 0, True, True), ('T5Ca1', sh5, sl5, 1, True, True),
                                                ('T15a0', sh15, sl15, 0, False, True), ('T15a1', sh15, sl15, 1, False, True)]:
                R, X = run(ent[keep], sd[keep], st[keep], o5, h5, l5, c5, swh, swl, gap5, 288, arm, cx, trl)
                g = np.isfinite(R); en = o5[ent[keep]][g]; risk = (en - st[keep][g]) * sd[keep][g]
                tt = f.time.to_numpy()[idx[keep]][g]
                rows.append(pd.DataFrame(dict(sym=sym, stop=stn, mng=mn, t=tt, side=sd[keep][g], num=num[keep][g], R0=R[g], cR=COST[sym] / risk,
                                              mins=(X[g] - ent[keep][g]) * 5, wid=wid[keep][g],
                                              half=np.where(tt < np.datetime64(pd.Timestamp(SPLIT[sym])), 1, 2))))
        print(sym, len(idx), flush=True)
    d = pd.concat(rows, ignore_index=True); d['R'] = d.R0 - d.cR; d.to_pickle('/home/user/trendlab/st/r5.pkl')

if __name__ == '__main__': main()
