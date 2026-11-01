"""H1 MA20 / MA75 cross -> 1st, 2nd, 3rd pullback entries, with conditions that may tell a trend start from a range cross.
Every candidate entry is simulated (stop under the pullback low; exits: 2R, 3R, H1 swing trail, MA cross back) and tagged with
its conditions, so the conditions can be compared afterwards (dev: EURUSD / XAUUSD / US500, check: the other 13)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition.pivots import pivot_events, atr as atr7
from lab import load, COST, DEV, OOS

def simulate(o, hi, lo, c, A, conf, i, s, en, sl, cross_back, kind):
    """exit of one trade from bar i+1. kind: tp2 / tp3 / trail (H1 swings from +1R) / ma (MA20 crosses back over MA75)"""
    risk = (en - sl) * s; tp = en + s * (2 if kind == 'tp2' else 3) * risk if kind in ('tp2', 'tp3') else None; on = False
    for j in range(i + 1, min(len(c), i + 24 * 120)):
        if kind == 'trail' and on:
            for e in conf.get(j - 1, []):
                if e['kind'] == ('lo' if s == 1 else 'hi'):
                    ns = e['price'] - s * 0.3 * A[j - 1]
                    if (ns - sl) * s > 0: sl = ns
        if (lo[j] <= sl) if s == 1 else (hi[j] >= sl):
            return ((min(o[j], sl) if s == 1 else max(o[j], sl)) - en) * s / risk, j
        if tp is not None and ((hi[j] >= tp) if s == 1 else (lo[j] <= tp)):
            return (tp - en) * s / risk, j
        if not on and ((hi[j] - en) if s == 1 else (en - lo[j])) >= risk: on = True
        if kind == 'ma' and cross_back[j]:
            return (c[j] - en) * s / risk, j
    return (c[min(len(c) - 1, i + 24 * 120 - 1)] - en) * s / risk, min(len(c) - 1, i + 24 * 120 - 1)

def run(sym, max_k=3, max_bars=240):
    h, d = load(sym); o, hi, lo, c = (h[z].to_numpy(float) for z in 'ohlc'); T = h.t.to_numpy(); A = atr7(h); cost = COST[sym]
    m20 = pd.Series(c).rolling(20).mean().to_numpy(); m75 = pd.Series(c).rolling(75).mean().to_numpy()
    up = m20 > m75; cross = np.r_[False, up[1:] != up[:-1]] & ~np.isnan(m75)
    ncross = pd.Series(cross.astype(int)).rolling(300).sum().to_numpy()
    h4 = h.set_index('t').resample('4h', label='left', closed='left').agg(dict(c='last')).dropna()
    h4u = (h4.c.rolling(20).mean() > h4.c.rolling(75).mean()).astype(int) - (h4.c.rolling(20).mean() < h4.c.rolling(75).mean()).astype(int)
    h4s = h4u.shift(1).reindex(pd.to_datetime(h.t).dt.floor('4h')).ffill().fillna(0).to_numpy()   # the last CLOSED H4 bar
    ev = sorted(pivot_events(h[['o', 'h', 'l', 'c']]), key=lambda e: e['available_idx']); conf = {}
    for e in ev: conf.setdefault(e['available_idx'], []).append(e)
    piv = []                                                    # (available bar, kind, anchor bar, price), known pivots in time order
    for e in ev: piv.append((e['available_idx'], e['kind'], e['idx'], e['price']))
    PA = np.array([p[0] for p in piv])
    rows = []
    for i0 in np.flatnonzero(cross):
        if i0 < 400 or i0 + 5 >= len(c): continue
        s = 1 if up[i0] else -1
        pre_hi = hi[i0 - 100:i0].max() if s == 1 else lo[i0 - 100:i0].min()          # the range high (low) before the cross
        known = [p for p in piv[:np.searchsorted(PA, i0, 'right')]]
        opp = [(a, p) for _, k, a, p in known if k == ('hi' if s == 1 else 'lo')][-2:]   # last two counter swings (for the trend line)
        tl = None
        if len(opp) == 2 and (opp[1][1] - opp[0][1]) * s < 0:
            tl = (opp[0][0], opp[0][1], (opp[1][1] - opp[0][1]) / (opp[1][0] - opp[0][0]))
        ext = hi[i0] if s == 1 else lo[i0]; k = 0; in_pb = False; pb_ext = None; broke = False; tl_broke = False; new_ext = True
        end = min(len(c) - 1, i0 + max_bars)
        for i in range(i0 + 1, end):
            if (m20[i] > m75[i]) != (s == 1): break                                      # crossed back: this cross is over
            if (hi[i] - pre_hi if s == 1 else pre_hi - lo[i]) > 0: broke = True
            if tl and not tl_broke:
                line = tl[1] + tl[2] * (i - tl[0])
                if (c[i] - line) * s > 0: tl_broke = True
            if (hi[i] - ext if s == 1 else ext - lo[i]) > 0:
                ext = hi[i] if s == 1 else lo[i]; new_ext = True; in_pb = False; continue
            near = (lo[i] <= m20[i] + 0.25 * A[i]) if s == 1 else (hi[i] >= m20[i] - 0.25 * A[i])
            if new_ext and near and ((lo[i] > m75[i]) if s == 1 else (hi[i] < m75[i])):
                if not in_pb: in_pb = True; pb_ext = lo[i] if s == 1 else hi[i]
            if in_pb:
                pb_ext = min(pb_ext, lo[i]) if s == 1 else max(pb_ext, hi[i])
                turn = (c[i] > hi[i - 1] and c[i] > o[i]) if s == 1 else (c[i] < lo[i - 1] and c[i] < o[i])
                if turn:
                    k += 1; en = c[i]; sl = pb_ext - s * 0.3 * A[i]
                    if (en - sl) * s > 0:
                        cb = (m20 < m75) if s == 1 else (m20 > m75)
                        r = dict(sym=sym, t=T[i], cross_t=T[i0], s=s, k=k, bars=i - i0, risk_atr=(en - sl) * s / A[i],
                                 ncross=ncross[i0], broke=broke, tl=bool(tl), tl_broke=tl_broke, slope=(m75[i] - m75[i - 10]) * s > 0,
                                 h4=h4s[i] == s, spread=(m20[i] - m75[i]) * s / A[i])
                        for kind in ('tp2', 'tp3', 'trail', 'ma'):
                            R, j = simulate(o, hi, lo, c, A, conf, i, s, en, sl, cb, kind)
                            r['R_' + kind] = R - cost / ((en - sl) * s)
                        rows.append(r)
                    in_pb = False; new_ext = False
                    if k >= max_k: break
    return pd.DataFrame(rows)

if __name__ == '__main__':
    out = [run(s) for s in sys.argv[1:]]
    pd.concat(out).to_pickle(f"/home/user/trendlab/x_{'_'.join(sys.argv[1:])}.pkl")
    print('done', sum(len(x) for x in out))
