"""Ensembles instead of one best setting: for each instrument x family, ALL settings that pass the first-half bar
(PF >= 1.15, n >= 40), each traded at 1/n size. Less dependent on one lucky setting. Builds feat/ens.pkl and reports halves."""
import glob, os, sys, numpy as np, pandas as pd, new_summary as N
S = N.S; pf = N.pf
FAM = {'L': 'tl_*.csv', 'A': 'retest_*.csv', 'RT': 'regime2_*.csv', 'J3': 'turn/j3_h*.csv', 'J2': 'turn/jt*.csv', 'EV': 'session/*.csv',
       'Q': 'q/Q_*.csv', 'PB2': 'pb2/PB2_*.csv', 'S': 'st2/S_*.csv'}
out = []; rows = []
for sym in N.COST:
    for fam, pat in FAM.items():
        sel = []
        for p in sorted(glob.glob(f'{S}/ws_{sym}/research/dow_strategy/results/{pat}')):
            try: x = N.load(sym, p.split('/results/')[1])
            except Exception: x = None
            if x is None: continue
            a = x[x.half == 1].R
            if len(a) >= 40 and pf(a) >= 1.15: sel.append(x)
        if len(sel) < 3: continue
        E = pd.concat(sel, ignore_index=True); E['R'] = E.R / len(sel); E['ea'] = fam + 'e'; E['pair'] = sym; E['key'] = f'{fam}e@{sym}'
        a = E[E.half == 1].R; b = E[E.half == 2].R
        rows.append(dict(sym=sym, fam=fam, 本数=len(sel), 前半R=a.sum(), 前半PF=pf(a), 後半R=b.sum(), 後半PF=pf(b))); out.append(E)
D = pd.DataFrame(rows); print(D.round(2).to_string(index=False))
pd.concat(out, ignore_index=True).to_pickle(f'{S}/feat/ens.pkl')
