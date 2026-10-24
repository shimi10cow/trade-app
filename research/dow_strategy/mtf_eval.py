"""EA trades right after an M15 impulse line break (mtf_break.py), split by the H1 line state at that moment.
 'old side' : trade in the direction of the broken line (buy after a rising M15 line broke) within N hours of the break and
              before the old extreme is regained -> the user's 'be careful for a while' (block candidate)
 'new side' : trade in the break direction (sell after the rising line broke) within N hours -> 'don't sell right away'
Mean R by half; a block helps if the old-side trades are below the rest in both halves."""
import glob, numpy as np, pandas as pd
import trade_pool as TP
S = TP.S
X = TP.load_all()
out = []
for f in sorted(glob.glob(f'{S}/feat/m15brk_*.pkl')):
    sym = f.split('m15brk_')[1][:-4]; D = pd.read_pickle(f); g = X[X.pair == sym].reset_index(drop=True)
    if not len(g): continue
    tt = g.tt.to_numpy()
    for N in (1, 2, 4, 8):
        for h1 in ('推進', '調整'):
            for rel in ('old', 'new'):
                hit = np.zeros(len(g), bool)
                for sd in (1, -1):
                    b = D[(D.side == sd) & (D.kind == h1)].sort_values('t'); bt = b.t.to_numpy()
                    m = (g.side == (sd if rel == 'old' else -sd)).to_numpy(); t = tt[m]
                    j = np.searchsorted(bt, t, 'right') - 1; jj = np.maximum(j, 0)
                    ok = (j >= 0) & (t - bt[jj] <= np.timedelta64(N, 'h'))
                    if rel == 'old': ok &= t < b.until.to_numpy()[jj]
                    hit[np.nonzero(m)[0][ok]] = True
                for grp, msk in (('全EA', np.ones(len(g), bool)), ('採用', g.adopt.to_numpy())):
                    for h in (1, 2):
                        mm = msk & (g.half == h).to_numpy()
                        if not mm.any(): continue
                        out.append(dict(sym=sym, N=N, h1=h1, rel=rel, grp=grp, half=h, n=int((hit & mm).sum()),
                                        mean=g.R[hit & mm].mean(), sumR=g.R[hit & mm].sum(), rest=g.R[~hit & mm].mean()))
    # the user's end-of-trend order: M15 line broke first, then the H1 line (within 16h) vs the H1 line alone
    H = pd.read_pickle(f'{S}/feat/h1blk_{sym}.pkl'); H = H[H['mode'] == 'redraw'].copy()
    H['seq'] = [('M15→H1' if ((D.side == x.side) & (D.t < x.t) & (D.t >= x.t - pd.Timedelta('16h'))).any() else 'H1だけ') for x in H.itertuples()]
    for N in (4, 12, 72):
        for sq in ('M15→H1', 'H1だけ'):
            hit = np.zeros(len(g), bool)
            for sd in (1, -1):
                b = H[(H.side == sd) & (H.seq == sq)].sort_values('t'); bt = b.t.to_numpy()
                m = (g.side == sd).to_numpy(); t = tt[m]
                j = np.searchsorted(bt, t, 'right') - 1; jj = np.maximum(j, 0)
                ok = (j >= 0) & (t - bt[jj] <= np.timedelta64(N, 'h')) & (t < b.until.to_numpy()[jj])
                hit[np.nonzero(m)[0][ok]] = True
            for grp, msk in (('全EA', np.ones(len(g), bool)), ('採用', g.adopt.to_numpy())):
                for h in (1, 2):
                    mm = msk & (g.half == h).to_numpy()
                    if not mm.any(): continue
                    out.append(dict(sym=sym, N=N, h1=sq, rel='seq', grp=grp, half=h, n=int((hit & mm).sum()),
                                    mean=g.R[hit & mm].mean(), sumR=g.R[hit & mm].sum(), rest=g.R[~hit & mm].mean()))
R = pd.DataFrame(out); R.to_pickle(f'{S}/feat/mtf_eval.pkl')
pd.set_option('display.width', 240)
for rel in ('old', 'new', 'seq'):
    print(f'\n######## {rel}（{dict(old="M15の線の向きに入った", new="M15を割った方向に入った", seq="H1の線を割った後、元の向きに入った")[rel]}）')
    t = R[R.rel == rel].pivot_table(index=['grp', 'N', 'h1', 'sym'], columns='half', values=['n', 'mean', 'rest', 'sumR']).round(2)
    print(t.to_string())
    P = R[R.rel == rel].groupby(['grp', 'N', 'h1', 'half']).apply(lambda d: pd.Series(dict(n=d.n.sum(), sumR=d.sumR.sum(), mean=d.sumR.sum() / max(d.n.sum(), 1)))).unstack('half').round(2)
    print('\n-- 銘柄合計'); print(P.to_string())
