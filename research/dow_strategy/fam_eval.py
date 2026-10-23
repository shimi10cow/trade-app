"""Generic evaluation of a setting grid (results/<sub>/<prefix>_*.csv) across instruments, XM costs, first-half choice.
usage: python fam_eval.py <sub/prefix> SYM [SYM...]   e.g. idip/D US30 US500 JP225"""
import glob, os, sys, numpy as np, pandas as pd, new_summary as N
S = N.S; pf = N.pf
OLD = {'EURUSD': 0.0, 'USDJPY': 0.3e-4, 'EURJPY': 0.8e-4, 'GBPUSD': 0.4e-4, 'XAUUSD': 1.3e-4, 'BTCUSD': 6.8e-4}
SPLIT = dict(N.SPLIT, BTCUSD=((2017, 2021), (2022, 2026)))
pat, syms = sys.argv[1], sys.argv[2:]
def load(sym, f):
    if sym in N.COST: return N.load(sym, f.split('/results/')[1])
    d = pd.read_csv(f)
    if not len(d): return None
    (a0, a1), (b0, b1) = SPLIT.get(sym, ((2005, 2015), (2016, 2026)))
    x = pd.DataFrame(dict(tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), R=d.R - OLD[sym] / d.risk, side=d.side, risk=d.risk)); y = x.tt.dt.year
    x = x[(y >= a0) & (y <= b1)].copy(); x['half'] = np.where(x.tt.dt.year <= a1, 1, 2); return x
rows = []; ALL = []
for sym in syms:
    d = '/home/user/trade-app/research/dow_strategy/results' if sym == 'EURUSD' else f'{S}/ws_{sym}/research/dow_strategy/results'
    for f in sorted(glob.glob(f'{d}/{pat}_*.csv')):
        x = load(sym, f)
        if x is None or not len(x): continue
        cfg = os.path.basename(f)[:-4]; a = x[x.half == 1].R; b = x[x.half == 2].R
        rows.append(dict(sym=sym, cfg=cfg, n1=len(a), R1=a.sum(), PF1=pf(a), n2=len(b), R2=b.sum(), PF2=pf(b)))
        ALL.append(x.assign(sym=sym, cfg=cfg))
D = pd.DataFrame(rows); A = pd.concat(ALL, ignore_index=True)
tag = pat.replace('/', '_'); D.to_csv(f'{S}/feat/fam_{tag}.csv', index=False); A.to_pickle(f'{S}/feat/fam_{tag}.pkl')
for sym, g in D.groupby('sym', sort=False):
    sel = g[(g.PF1 >= 1.15) & (g.n1 >= 30)]; b = sel.sort_values('PF1', ascending=False).head(1)
    both = g[(g.R1 > 0) & (g.R2 > 0)]
    print(f'{sym}: {len(g)} 設定、前後半とも黒字 {len(both)}、前半合格 {len(sel)} → 後半黒字 {(sel.R2 > 0).sum()}、PF相関 {np.corrcoef(g.PF1, g.PF2)[0,1]:+.2f}' +
          (f' | 前半最良 {b.cfg.iat[0]} {b.R1.iat[0]:+.0f}R PF{b.PF1.iat[0]:.2f}({b.n1.iat[0]}) → {b.R2.iat[0]:+.0f}R PF{b.PF2.iat[0]:.2f}({b.n2.iat[0]})' if len(b) else ''))
p = A.cfg.str.split('_')
print('\n### 作りの違い（各銘柄の平均R、前半/後半）')
for i in range(1, p.str.len().max()):
    A['k'] = p.str[i]
    g = A.groupby(['k', 'sym', 'half']).R.mean().unstack('half').round(2)
    print(f'-- 位置{i}'); print(g.unstack('sym').to_string())
