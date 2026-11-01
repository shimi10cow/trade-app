"""Same entries as the live EAs, different exits (post-hoc on M15). R in units of the initial risk, minus cost."""
import sys, glob, bisect, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition.pivots import pivot_events
SYMS = {'EURUSD': ['R@EURUSD', 'T2@EURUSD', 'L@EURUSD', 'A@EURUSD', 'C@EURUSD'], 'USDJPY': ['C@USDJPY', 'J2@USDJPY'],
        'XAUUSD': ['L2@XAUUSD', 'S@XAUUSD', 'Q@XAUUSD', 'DS@XAUUSD'], 'US500': ['M@US500', 'DS@US500'], 'JP225': ['DS@JP225']}
COST = 1.2e-4; K = 3.0; MAXD = 250
col = lambda d, *n: next((d[c] for c in n if c in d), None)
out = []
for sym, eas in SYMS.items():
    m = pd.read_pickle(f'/home/user/trend_diag/m15_{sym}.pkl').reset_index(drop=True); T = pd.to_datetime(m.t).to_numpy()
    H, L, C = m.h.to_numpy(), m.l.to_numpy(), m.c.to_numpy()
    d1 = m.set_index('t').resample('1D').agg(dict(h='max', l='min', c='last')).dropna(); pc = d1.c.shift()
    atr = np.maximum(d1.h - d1.l, np.maximum((d1.h - pc).abs(), (d1.l - pc).abs())).rolling(20).mean().shift(1)   # yesterday's ATR
    A = atr.reindex(pd.to_datetime(m.t).dt.normalize()).to_numpy()
    h4 = m.set_index('t').resample('4h', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    ev = pivot_events(h4[['o', 'h', 'l', 'c']]); C4 = (pd.to_datetime(h4.t) + pd.Timedelta('4h')).to_numpy()
    piv = {'lo': [], 'hi': []}; last = {}
    for e in sorted(ev, key=lambda e: e['available_idx']):
        last[e['id']] = e; piv[e['kind']].append((C4[e['available_idx']], e['price']))
    PT = {k: np.array([x[0] for x in v]) for k, v in piv.items()}; PP = {k: np.array([x[1] for x in v]) for k, v in piv.items()}
    for k in eas:
        for f in glob.glob(f"/home/user/trend_diag/tr_{k.replace('@', '_')}.pkl"):
            x = pd.read_pickle(f)
            for t, s, en, sl0, ex, ext, r0 in zip(pd.to_datetime(col(x, 't')), col(x, 'side').astype(int), col(x, 'entry'), col(x, 'sl0'), col(x, 'exit'), pd.to_datetime(col(x, 'exit_t')), col(x, 'R')):
                i0 = np.searchsorted(T, np.datetime64(t)); i1 = min(len(T), i0 + MAXD * 96); risk = abs(en - sl0)
                if not risk or i0 >= len(T) - 2: continue
                h, l, c, a, tt = H[i0:i1], L[i0:i1], C[i0:i1], A[i0:i1], T[i0:i1]
                fav = (h - en) if s == 1 else (en - l); act = np.maximum.accumulate(fav) >= risk             # +1R reached (trail on)
                def run(stop):
                    stop = np.where(act, stop, sl0); stop = np.maximum.accumulate(stop) if s == 1 else np.minimum.accumulate(stop)
                    stop = np.maximum(stop, sl0) if s == 1 else np.minimum(stop, sl0)
                    hit = (l <= stop) if s == 1 else (h >= stop); j = int(np.argmax(hit)) if hit.any() else len(c) - 1
                    px = stop[j] if hit.any() else c[j]
                    return (px - en) * s / risk - COST / risk, tt[j]
                ext_ = np.maximum.accumulate(h) if s == 1 else np.minimum.accumulate(l)
                rd, td = run(ext_ - s * K * np.nan_to_num(a, nan=1e9))                                      # D1 chandelier
                kd = 'lo' if s == 1 else 'hi'; jj = np.searchsorted(PT[kd], tt, side='right') - 1
                p4 = np.where(jj >= 0, PP[kd][np.clip(jj, 0, None)], sl0); rh, th = run(p4)                  # H4 Dow swing
                out.append(dict(sym=sym, ea=k, t=t, R0=r0, Rd=rd, Rh=rh, Rmix=0.5 * r0 + 0.5 * rd, t0=ext, td=pd.Timestamp(td), th=pd.Timestamp(th),
                                hold0=(ext - t).total_seconds() / 86400, holdd=(pd.Timestamp(td) - t).total_seconds() / 86400))
D = pd.DataFrame(out); D.to_pickle('/home/user/trend_diag/exits.pkl')
def stats(g, c, tcol):
    g = g.sort_values(tcol); eq = g[c].cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    return f"{g[c].sum():+7.0f}R 勝率{np.mean(g[c] > 0):4.0%} DD{dd:5.0f}R"
lab = [('R0', 't0', '今のまま'), ('Rd', 'td', '日足で引っ張る'), ('Rh', 'th', 'H4ダウで引っ張る'), ('Rmix', 'td', '半分ずつ')]
for name, g in list(D.groupby('sym')) + [('全部', D)]:
    mid = g.t.median(); print(f"\n== {name}（{len(g)} 回）")
    for c, tc, l in lab:
        a, b = g[g.t < mid], g[g.t >= mid]
        print(f"  {l:10s} {stats(g, c, tc)}  前半 {a[c].sum():+6.0f}R / 後半 {b[c].sum():+6.0f}R")
print('\n持つ日数（真ん中）今 {:.1f} 日 → 日足で引っ張る {:.1f} 日'.format(D.hold0.median(), D.holdd.median()))
for ea, g in D.groupby('ea'):
    print(f"  {ea:10s} 今 {g.R0.sum():+5.0f}R  日足 {g.Rd.sum():+5.0f}R  H4 {g.Rh.sum():+5.0f}R  半分 {g.Rmix.sum():+5.0f}R")
