"""Big trends (D1 zigzag) vs what the EAs did inside them."""
import sys, glob, numpy as np, pandas as pd
SYMS = {'EURUSD': ['R@EURUSD', 'T2@EURUSD', 'L@EURUSD', 'A@EURUSD', 'C@EURUSD'], 'USDJPY': ['C@USDJPY', 'J2@USDJPY'],
        'XAUUSD': ['L2@XAUUSD', 'S@XAUUSD', 'Q@XAUUSD', 'DS@XAUUSD'], 'US500': ['M@US500', 'DS@US500'], 'JP225': ['DS@JP225']}
REV, BIG = float(sys.argv[1]) if len(sys.argv) > 1 else 3.0, float(sys.argv[2]) if len(sys.argv) > 2 else 8.0
col = lambda d, *n: next((d[c] for c in n if c in d), None)
def legs(m):
    d = m.set_index('t').resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna()
    pc = d.c.shift(); atr = np.maximum(d.h - d.l, np.maximum((d.h - pc).abs(), (d.l - pc).abs())).rolling(20).mean()
    out = []; dirn = 0; ext_t = d.index[20]; ext = d.c.iloc[20]; st_t, st = ext_t, ext
    for t, r in d.iloc[21:].iterrows():
        a = atr.loc[t]
        if dirn >= 0 and r.h > ext and dirn == 1: ext, ext_t = r.h, t
        if dirn <= 0 and r.l < ext and dirn == -1: ext, ext_t = r.l, t
        if dirn == 0:
            if r.h > st + REV * a: dirn, ext, ext_t = 1, r.h, t
            elif r.l < st - REV * a: dirn, ext, ext_t = -1, r.l, t
            continue
        if dirn == 1 and r.l < ext - REV * a:
            out.append((st_t, ext_t, 1, st, ext, atr.loc[st_t])); st_t, st, dirn, ext, ext_t = ext_t, ext, -1, r.l, t
        elif dirn == -1 and r.h > ext + REV * a:
            out.append((st_t, ext_t, -1, st, ext, atr.loc[st_t])); st_t, st, dirn, ext, ext_t = ext_t, ext, 1, r.h, t
    L = pd.DataFrame(out, columns=['ts', 'te', 'dir', 'p0', 'p1', 'atr']); L['size_atr'] = (L.p1 - L.p0).abs() / L.atr
    return L
rows = []; tot = []
for sym, eas in SYMS.items():
    try:
        m = pd.read_pickle(f'/home/user/trend_diag/m15_{sym}.pkl')
    except FileNotFoundError:
        continue
    T = []
    for k in eas:
        for f in glob.glob(f"/home/user/trend_diag/tr_{k.replace('@', '_')}.pkl"):
            x = pd.read_pickle(f)
            if not len(x): continue
            T.append(pd.DataFrame(dict(ea=k, t=pd.to_datetime(col(x, 't')), side=col(x, 'side').astype(int), entry=col(x, 'entry', 'EntryPrice'),
                                       exit=col(x, 'exit', 'ExitPrice'), exit_t=pd.to_datetime(col(x, 'exit_t', 'ExitTime')), R=col(x, 'R'))))
    if not T: continue
    T = pd.concat(T, ignore_index=True); T = T[T.t >= T.t.min()]
    L = legs(m); L = L[(L.ts >= T.t.min()) & (L.size_atr >= BIG)]
    tot.append(dict(sym=sym, R_all=T.R.sum(), n_all=len(T)))
    for _, g in L.iterrows():
        S = abs(g.p1 - g.p0)
        w = T[(T.t >= g.ts) & (T.t < g.te) & (T.side == g.dir)]; c = T[(T.t >= g.ts) & (T.t < g.te) & (T.side != g.dir)]
        r = dict(sym=sym, ts=g.ts, te=g.te, dir=g.dir, size_atr=g.size_atr, days=(g.te - g.ts).days, n_with=len(w), R_with=w.R.sum(), n_against=len(c), R_against=c.R.sum())
        if len(w):
            w = w.assign(cap=(w.exit - w.entry) * g.dir / S, pos=(w.entry - g.p0) * g.dir / S, left=(g.p1 - w.exit) * g.dir / S)
            b = w.loc[w.cap.idxmax()]
            r.update(first_pos=w.pos.min(), best_cap=b.cap, best_left=b.left, best_R=b.R, stopped=int((w.R <= -0.9).sum()), sum_cap=w.cap.sum())
        rows.append(r)
D = pd.DataFrame(rows); pd.set_option('display.width', 220)
print(f'大きなトレンド：日足で ATR×{REV} 戻したら終わりの波のうち、ATR×{BIG} 以上動いたもの')
for sym, g in list(D.groupby('sym')) + [('全部', D)]:
    e = g[g.n_with > 0]
    print(f"\n== {sym}: {len(g)} 本（平均 {g.size_atr.mean():.0f}×ATR・{g.days.mean():.0f} 日）")
    print(f"  同じ向きで入った波 {len(e)}/{len(g)}（{len(e)/max(1,len(g)):.0%}）、1 本あたり {g.n_with.mean():.1f} 回・{g.R_with.mean():+.2f}R、逆向き {g.n_against.mean():.1f} 回・{g.R_against.mean():+.2f}R")
    if len(e):
        print(f"  最初に入った位置：波の {e.first_pos.median():.0%} 地点（真ん中）")
        print(f"  一番取れたトレード：波の {e.best_cap.median():.0%} を取った（真ん中）、降りた後に残った分 {e.best_left.median():.0%}、そのトレード {e.best_R.median():+.1f}R")
        print(f"  入ったトレードを全部足すと波の {e.sum_cap.median():.0%}（真ん中）、損切りされた回 平均 {e.stopped.mean():.1f}")
for x in tot:
    k = D[D.sym == x['sym']]
    print(f"  {x['sym']}: EA 全体 {x['n_all']} 回 {x['R_all']:+.0f}R のうち、大きな波の中・同じ向き {k.R_with.sum():+.0f}R、逆向き {k.R_against.sum():+.0f}R")
D.to_pickle(f'/home/user/trend_diag/legs_{REV}_{BIG}.pkl')
