"""Summary of all EAs on the new instruments (2026-10-22). Workspaces use log prices (1 'pip' = 0.01 %); trade files were
made with a 0.012 % cost, re-costed here with each instrument's XM KIWAMI-based cost (wide side + margin).
Core EAs at their fixed settings; families (Q, PB2, S) chosen on the first half only (PF >= 1.15, n >= 40) then checked."""
import sys, glob, os, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
COST = {'GBPJPY': ('pip', 3.3, 0.01), 'AUDJPY': ('pip', 1.5, 0.01), 'CHFJPY': ('pip', 1.5, 0.01), 'CADJPY': ('pip', 2.5, 0.01),
        'AUDUSD': ('pip', 1.5, 1e-4), 'USDCAD': ('pip', 2.0, 1e-4), 'USDCHF': ('pip', 2.0, 1e-4), 'XAGUSD': ('pct', 0.05), 'US30': ('pct', 0.01)}
SPLIT = {'US30': ((2015, 2020), (2021, 2026)), 'AUDUSD': ((2010, 2015), (2016, 2026)), 'CADJPY': ((2006, 2015), (2016, 2026))}
CORE = [('R', 'regime2_R2c.csv'), ('T', 'regime2_T1t.csv'), ('L', 'tl_N2.csv'), ('A', 'retest_N1.csv'), ('C', 'step2/cl15_md4tri.csv'),
        ('J2', 'turn/jt2_h1major+hour0_10.csv'), ('J3', 'turn/j3_h41_s0_h1prot.csv'), ('EV', 'session/ev_18-21+0-3.csv'), ('P', 'pb/P4_maj0_rs0.5.csv')]
FAM = {'Q': 'q/Q_*.csv', 'PB2': 'pb2/PB2_*.csv', 'S': 'st2/S_*.csv'}
def pf(r): return r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
def load(sym, f):
    p = f'{S}/ws_{sym}/research/dow_strategy/results/{f}'
    if not os.path.exists(p): return None
    d = pd.read_csv(p)
    if not len(d): return None
    if 'Rc' in d: t = pd.to_datetime(d.time); R = d.Rc.to_numpy(); et = pd.to_datetime(d.ExitTime)
    else: t = pd.to_datetime(d.t); R = d.R.to_numpy(); et = pd.to_datetime(d.exit_t)
    c = COST[sym]; cl = c[1] / 100 if c[0] == 'pct' else c[1] * c[2] / np.exp(d.entry.to_numpy())
    R = R - (cl - 1.2e-4) / d.risk.to_numpy()
    (a0, a1), (b0, b1) = SPLIT.get(sym, ((2005, 2015), (2016, 2026)))
    x = pd.DataFrame(dict(tt=t, et=et, R=R, side=d.side.to_numpy(), risk=d.risk.to_numpy())); y = x.tt.dt.year
    x = x[(y >= a0) & (y <= b1)].copy(); x['half'] = np.where(x.tt.dt.year <= a1, 1, 2); return x
def stat(x):
    r1 = x[x.half == 1].R; r2 = x[x.half == 2].R
    return dict(n1=len(r1), R1=r1.sum(), PF1=pf(r1), n2=len(r2), R2=r2.sum(), PF2=pf(r2), top5=x.R.nlargest(5).sum(), buyR=x[x.side == 1].R.sum(), sellR=x[x.side == -1].R.sum())
if __name__ == '__main__':
    syms = sys.argv[1:] or list(COST)
    rows = []; fam = []
    for sym in syms:
        for ea, f in CORE:
            x = load(sym, f)
            if x is not None: rows.append(dict(sym=sym, ea=ea, cfg=f, **stat(x)))
        for ea, pat in FAM.items():
            for p in sorted(glob.glob(f'{S}/ws_{sym}/research/dow_strategy/results/{pat}')):
                x = load(sym, p.split('/results/')[1])
                if x is not None: fam.append(dict(sym=sym, ea=ea, cfg=os.path.basename(p)[:-4], **stat(x)))
    C = pd.DataFrame(rows); F = pd.DataFrame(fam)
    C.to_csv(f'{S}/feat/new_core.csv', index=False); F.to_csv(f'{S}/feat/new_fam.csv', index=False)
    for sym, g in C.groupby('sym', sort=False):
        print(f'\n== {sym}'); print(g[['ea', 'n1', 'R1', 'PF1', 'n2', 'R2', 'PF2', 'top5', 'buyR', 'sellR']].round(2).to_string(index=False))
        h = F[F.sym == sym]
        for ea, q in h.groupby('ea'):
            sel = q[(q.PF1 >= 1.15) & (q.n1 >= 40)]
            best = sel.sort_values('PF1', ascending=False).head(1)
            print(f'  {ea}: {len(q)} 設定、前半で選べる {len(sel)}、うち後半 PF>1 {(sel.PF2>1).sum()}、前後半 PF の相関 {np.corrcoef(q.PF1, q.PF2)[0,1]:+.2f}' +
                  (f' | 前半最良 {best.cfg.iat[0]} 前半 {best.R1.iat[0]:+.0f}R PF{best.PF1.iat[0]:.2f}（{best.n1.iat[0]}）／後半 {best.R2.iat[0]:+.0f}R PF{best.PF2.iat[0]:.2f}（{best.n2.iat[0]}）' if len(best) else ''))
