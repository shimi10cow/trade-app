"""Cycle 1 (2026-10-22): rules that need only the trade lists.
 a) own recent results: skip when the EA's last N closed trades (closed before this entry) sum below a level
 b) agreement: another EA entered the same pair & side in the previous X hours
 c) conflict: another EA holds the opposite side on the same pair at entry
 d) streak after a big win / loss
For each rule: per EA×pair, the R lost/gained by skipping, in each half; count EAs improved in both halves."""
import sys
import numpy as np, pandas as pd
T = pd.read_pickle(sys.argv[1])
def judge(name, mask):
    """mask True = skip"""
    rows = []
    for k, g in T.groupby('key'):
        m = mask.loc[g.index]
        d1 = -g.R[m & (g.half == 1)].sum(); d2 = -g.R[m & (g.half == 2)].sum()
        rows.append((k, g.adopted.iat[0], d1, d2, m.mean()))
    r = pd.DataFrame(rows, columns=['key', 'ad', 'd1', 'd2', 'skip'])
    both = ((r.d1 > 0) & (r.d2 > 0)).sum(); worse = ((r.d1 < 0) & (r.d2 < 0)).sum()
    a = r[r.ad]
    print(f'{name:34s} 外す{r.skip.mean():4.0%} 全EA 前半{r.d1.sum():+7.1f} 後半{r.d2.sum():+7.1f} 両方改善{both:2d} 両方悪化{worse:2d} | 採用 {a.d1.sum():+6.1f}/{a.d2.sum():+6.1f} ({((a.d1>0)&(a.d2>0)).sum()}/{len(a)})', flush=True)
    return r
# a) own recent results
for N in (5, 10, 20):
    for lo in (-3, -1, 0):
        m = pd.Series(False, index=T.index)
        for k, g in T.groupby('key'):
            et = g.et.to_numpy(); tt = g.tt.to_numpy(); R = g.R.to_numpy(); o = np.argsort(et); ets = et[o]; Rs = R[o]
            cs = np.r_[0, np.cumsum(Rs)]
            n = np.searchsorted(ets, tt, 'right')
            s = cs[n] - cs[np.maximum(0, n - N)]
            m.loc[g.index] = (n >= N) & (s < lo)
        judge(f'a 直近{N}回の合計<{lo}', m)
# b) agreement
tt = T.tt.to_numpy(); pr = T.pair.to_numpy(); sd = T.side.to_numpy(); ea = T.ea.to_numpy()
for X in (4, 12, 24):
    agree = np.zeros(len(T), bool); opp = np.zeros(len(T), bool)
    for p in np.unique(pr):
        ix = np.where(pr == p)[0]
        for i in ix:
            w = ix[(tt[ix] < tt[i]) & (tt[ix] >= tt[i] - np.timedelta64(X, 'h')) & (ea[ix] != ea[i])]
            agree[i] = (sd[w] == sd[i]).any(); opp[i] = (sd[w] != sd[i]).any()
    judge(f'b 他EAが{X}h内に同方向 なら外す', pd.Series(agree, T.index))
    judge(f'b 他EAが{X}h内に同方向 でなければ外す', pd.Series(~agree, T.index))
    judge(f'b 他EAが{X}h内に逆方向 なら外す', pd.Series(opp, T.index))
# c) conflict with open opposite position
et = T.et.to_numpy(); hold_opp = np.zeros(len(T), bool); hold_same = np.zeros(len(T), bool)
for p in np.unique(pr):
    ix = np.where(pr == p)[0]
    for i in ix:
        w = ix[(tt[ix] < tt[i]) & (et[ix] > tt[i]) & (ea[ix] != ea[i])]
        hold_opp[i] = (sd[w] != sd[i]).any(); hold_same[i] = (sd[w] == sd[i]).any()
judge('c 他EAが逆を保有中 なら外す', pd.Series(hold_opp, T.index))
judge('c 他EAが同方向を保有中 なら外す', pd.Series(hold_same, T.index))
# d) after last trade outcome of same EA
for lab, f in (('直前が負け', lambda r: r < 0), ('直前が+2R以上', lambda r: r >= 2), ('直前2回連続負け', None)):
    m = pd.Series(False, index=T.index)
    for k, g in T.groupby('key'):
        et_ = g.et.to_numpy(); o = np.argsort(et_); ets = et_[o]; Rs = g.R.to_numpy()[o]
        n = np.searchsorted(ets, g.tt.to_numpy(), 'right')
        if f is None: v = np.array([j >= 2 and Rs[j - 1] < 0 and Rs[j - 2] < 0 for j in n])
        else: v = np.array([j >= 1 and f(Rs[j - 1]) for j in n])
        m.loc[g.index] = v
    judge(f'd {lab} なら外す', m)
