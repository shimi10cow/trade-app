"""Variant sweep on the new instruments: every TL / retest / regime(R,T) / J3 / session / Q / PB2 / S setting.
Per instrument x family: settings passing the first-half bar (PF >= 1.15, n >= 40) -> how many stay PF > 1 in the second half,
first-half best -> second half. Saves the first-half best per family to feat/sweep_best.pkl."""
import glob, os, sys, numpy as np, pandas as pd, new_summary as N
S = N.S; pf = N.pf
FAM = {'L(TL)': 'tl_*.csv', 'A(retest)': 'retest_*.csv', 'RT(regime)': 'regime2_*.csv', 'J3': 'turn/j3_h*.csv',
       'C': 'step2/*.csv', 'J2': 'turn/jt*.csv', 'EV': 'session/*.csv', 'P': 'pb/*.csv', 'Q': 'q/Q_*.csv', 'PB2': 'pb2/PB2_*.csv', 'S': 'st2/S_*.csv'}
syms = sys.argv[1:] or list(N.COST)
rows = []; best = []
for sym in syms:
    for fam, pat in FAM.items():
        st = []
        for p in sorted(glob.glob(f'{S}/ws_{sym}/research/dow_strategy/results/{pat}')):
            try: x = N.load(sym, p.split('/results/')[1])
            except Exception: x = None
            if x is None: continue
            a = x[x.half == 1].R; b = x[x.half == 2].R
            st.append((os.path.basename(p)[:-4], pf(a), len(a), a.sum(), pf(b), len(b), b.sum(), x))
        if not st: continue
        sel = [s for s in st if s[1] >= 1.15 and s[2] >= 40]
        r = dict(sym=sym, fam=fam, 設定=len(st), 選べる=len(sel), 後半黒字=sum(s[4] > 1 for s in sel),
                 相関=np.corrcoef([s[1] for s in st], [s[4] for s in st])[0, 1] if len(st) > 2 else np.nan)
        if sel:
            b = max(sel, key=lambda s: s[1]); r.update(最良=b[0], 前半=f'{b[3]:+.0f}R PF{b[1]:.2f}({b[2]})', 後半=f'{b[6]:+.0f}R PF{b[4]:.2f}({b[5]})')
            x = b[7].copy(); x['ea'] = fam.split('(')[0]; x['pair'] = sym; x['key'] = f"{x.ea.iat[0]}*@{sym}"; x['cfg'] = b[0]; best.append(x)
        rows.append(r)
D = pd.DataFrame(rows); pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 40)
for sym, g in D.groupby('sym', sort=False): print(f'\n== {sym}'); print(g.drop(columns='sym').round(2).to_string(index=False))
D.to_csv(f'{S}/feat/sweep_eval.csv', index=False)
if best: pd.concat(best, ignore_index=True).to_pickle(f'{S}/feat/sweep_best.pkl')
