"""Per-EA summary for gold/BTC workspaces with instrument split and cost scenarios (prices are log; 1 pip = 0.01%).
R files already include 1.2 pip cost; other costs: R_new = R - (cost-1.2)e-4/risk."""
import sys, numpy as np, pandas as pd
from pathlib import Path
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SRC = [('R', 'regime2_R2c.csv'), ('T', 'regime2_T1t.csv'), ('L', 'tl_N2.csv'), ('A', 'retest_N1.csv'), ('C', 'step2/cl15_md4tri.csv'),
       ('J2', 'turn/jt2_h1major+hour0_10.csv'), ('J3', 'turn/j3_h41_s0_h1prot.csv'), ('EV', 'session/ev_18-21+0-3.csv'), ('P', 'pb/P4_maj0_rs0.5.csv')]
CFG = {'XAUUSD': ((2005, 2015), (2016, 2026), (1.2, 2.5)), 'BTCUSD': ((2017, 2021), (2022, 2026), (4.0, 8.0))}
pf = lambda r: r[r > 0].sum() / max(1e-9, -r[r <= 0].sum())
for sym in sys.argv[1:]:
    D = Path(f'{S}/ws_{sym}/research/dow_strategy/results'); h1, h2, costs = CFG[sym]
    print(f'## {sym}（前半 {h1[0]}-{h1[1]} / 後半 {h2[0]}-{h2[1]}）')
    print('| EA | 回数/年 | 損切り中央(%) | ' + ' | '.join(f'コスト{c / 100:.3f}% 前半 | 後半 | DD' for c in costs) + ' |')
    for code, f in SRC:
        if not (D / f).exists():
            print(f'| {code} | （結果なし） |'); continue
        d = pd.read_csv(D / f)
        if 'Rc' in d: t, R = pd.to_datetime(d.time), d.Rc.to_numpy()
        else: t, R = pd.to_datetime(d.t), d.R.to_numpy()
        y = t.dt.year.to_numpy(); risk = d.risk.to_numpy()
        m = (y >= h1[0]) & (y <= h2[1]); yrs = h2[1] - h1[0] + 1
        cells = []
        for c in costs:
            r = R - (c - 1.2) * 1e-4 / risk
            a = r[m & (y <= h1[1])]; b = r[m & (y >= h2[0])]
            eq = np.cumsum(r[m][np.argsort(t[m].to_numpy())]); dd = (eq - np.maximum.accumulate(eq)).min() if len(eq) else 0
            cells.append(f'{a.sum():+.0f}R PF{pf(a):.2f} | {b.sum():+.0f}R PF{pf(b):.2f} | {dd:.0f}')
        print(f'| {code} | {m.sum() / yrs:.0f} | {np.median(risk[m]) * 100:.2f} | ' + ' | '.join(cells) + ' |')
