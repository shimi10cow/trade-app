"""US500 / JP225 / OIL (XM MT5, 2017-2026) on top of combo ④. Candidates picked on 2017-21 only:
core EAs with first-half PF >= 1.15 and n >= 30; families (Q, PB2, S) -> first-half best if >= 10 settings pass."""
import glob, os, pandas as pd, pfx, combo_stable as CS, new_summary as N
S = N.S; pf = N.pf; rows = []
for sym in ('US500', 'JP225', 'OIL'):
    for ea, f in N.CORE:
        x = N.load(sym, f)
        if x is None: continue
        a = x[x.half == 1].R
        if len(a) >= 30 and pf(a) >= 1.15: rows.append(x.assign(key=f'{ea}@{sym}', pair=sym))
    for ea, pat in N.FAM.items():
        st = []
        for p in glob.glob(f'{S}/ws_{sym}/research/dow_strategy/results/{pat}'):
            x = N.load(sym, p.split('/results/')[1])
            if x is None: continue
            a = x[x.half == 1].R
            if len(a) >= 30 and pf(a) >= 1.15: st.append((pf(a), x))
        if len(st) >= 10: rows.append(max(st, key=lambda z: z[0])[1].assign(key=f'{ea}@{sym}', pair=sym))
C = pd.concat(rows, ignore_index=True)
for k, g in C.groupby('key'):
    a = g[g.half == 1].R; b = g[g.half == 2].R
    print(f'{k:10s} 前半 {a.sum():+6.1f}R PF{pf(a):.2f}({len(a)}) 後半 {b.sum():+6.1f}R PF{pf(b):.2f}({len(b)})')
keys4 = CS.P['④ ③＋US30（T・Q）']; base = CS.mk(keys4); base['tt'] = pd.to_datetime(base.tt); base['et'] = pd.to_datetime(base.et)
pfx.ev(base, keys4, label='④ 基準')
for k in sorted(C.key.unique()): pfx.ev(base, keys4, C[C.key == k], label=f'④＋{k}')
pfx.ev(base, keys4, C, label=f'④＋候補すべて({C.key.nunique()})')
C.to_pickle(f'{S}/feat/new3_cands.pkl')
