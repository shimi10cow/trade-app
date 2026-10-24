"""Decelerating trend (user, 2026-10-23): when each redrawn H1 line is FLATTER than the one it replaced, a break of that flatter
line tends to start a correction / reversal. ratio = slope of the broken line / slope of the line it replaced (same leg).
Market: share of breaks where the old extreme is regained within 72h, by ratio bin. EA: trades entered in the old direction
while blocked (until regained, max 72h), by ratio bin and half."""
import glob, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
X = pd.read_pickle(f'{S}/feat/h1blk_eval.pkl') if False else None
import h1_break_eval as HE   # builds the trade table X (all EAs) on import
X = HE.X
bins = [0, 0.7, 1.0, 1.5, 99]; labs = ['緩く(0.7未満)', 'やや緩く(0.7-1)', 'やや急(1-1.5)', '急(1.5超)']
rows = []
for f in sorted(glob.glob(f'{S}/feat/h1blk_*.pkl')):
    sym = f.split('h1blk_')[1][:-4]; D = pd.read_pickle(f)
    if 'ratio' not in D: continue
    D = D[(D['mode'] == 'redraw') & D.ratio.notna()].copy(); D['bin'] = pd.cut(D.ratio, bins, labels=labs)
    D['regain'] = (D.until - D.t) < pd.Timedelta('71h')
    g = X[X.pair == sym]
    for b, d in D.groupby('bin', observed=True):
        blk = np.zeros(len(g), bool)
        for sd in (1, -1):
            bb = d[d.side == sd].sort_values('t'); m = (g.side == sd).to_numpy(); tt = g.tt.to_numpy()[m]
            j = np.searchsorted(bb.t.to_numpy(), tt, 'right') - 1; ok = (j >= 0) & (tt < bb.until.to_numpy()[np.maximum(j, 0)])
            blk[np.nonzero(m)[0][ok]] = True
        h = g.half.to_numpy()
        rows.append(dict(sym=sym, 角度=b, 割れ回数=len(d), 高安更新=d.regain.mean(), 止めた前半=g.R[blk & (h == 1)].mean(), 止めた後半=g.R[blk & (h == 2)].mean(),
                         回数前半=int((blk & (h == 1)).sum()), 回数後半=int((blk & (h == 2)).sum())))
R = pd.DataFrame(rows); pd.set_option('display.width', 200)
print(R.round(2).to_string(index=False))
