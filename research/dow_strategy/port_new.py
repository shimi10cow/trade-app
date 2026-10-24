"""Portfolio additions from the new instruments + unused EAs on existing ones (2026-10-22), XM costs.
Selection uses the FIRST half only: an EA x instrument is a candidate if first-half PF >= 1.15 and n >= 40.
Then: base (BASE9T2) + each candidate alone, + all candidates, + candidates grouped by EA, compared at same risk."""
import sys, glob, numpy as np, pandas as pd
import pfx, new_summary as N
S = N.S
T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl')
syms = [s for s in (__import__('os').environ.get('SYMS') or ' '.join(N.COST)).split() if __import__('os').path.isdir(f'{S}/ws_{s}')]
rows = []
for sym in syms:
    for ea, f in N.CORE:
        x = N.load(sym, f)
        if x is None: continue
        x = x.copy(); x['ea'] = ea; x['pair'] = sym; x['key'] = f'{ea}@{sym}'; rows.append(x)
    # families: if >= 10 settings pass the first-half bar, take the first-half best setting
    for ea, pat in N.FAM.items():
        st = []
        for p in sorted(glob.glob(f'{S}/ws_{sym}/research/dow_strategy/results/{pat}')):
            x = N.load(sym, p.split('/results/')[1])
            if x is None: continue
            a = x[x.half == 1].R
            if len(a) >= 40 and N.pf(a) >= 1.15: st.append((N.pf(a), p, x))
        if len(st) >= 10:
            b = max(st, key=lambda z: z[0]); x = b[2].copy(); x['ea'] = ea; x['pair'] = sym; x['key'] = f'{ea}@{sym}'; rows.append(x)
            print(f'{sym} {ea}: 前半で {len(st)} 設定 → {b[1].split("/")[-1]}')
NEW = pd.concat(rows, ignore_index=True)
ALL = pd.concat([T[~T.key.isin(pfx.BASE9T2) & (T.pair != 'BTCUSD')], NEW], ignore_index=True)
pf = N.pf
cand = []
for k, g in ALL.groupby('key'):
    a = g[g.half == 1].R; b = g[g.half == 2].R
    if len(a) >= 40 and pf(a) >= 1.15: cand.append((k, pf(a), pf(b), b.sum(), len(b)))
cand.sort(key=lambda c: -c[1])
print('候補（前半で選択）:'); [print(f'  {k:12s} 前半PF{a:.2f} → 後半PF{b:.2f} {r:+.1f}R ({n})') for k, a, b, r, n in cand]
keys = [c[0] for c in cand]
bs = '--fast' not in sys.argv
pfx.ev(T, pfx.BASE9T2, label='基準 BASE9T2(XM)', bs=bs)
newk = [k for k in keys if k.split('@')[1] in N.COST]; oldk = [k for k in keys if k not in newk]
for k in newk:
    pfx.ev(T, pfx.BASE9T2, ALL[ALL.key == k], label=f'+ {k}', bs=bs)
pfx.ev(T, pfx.BASE9T2, ALL[ALL.key.isin(newk)], label=f'+ 新銘柄の候補すべて({len(newk)})', bs=bs)
pfx.ev(T, pfx.BASE9T2, ALL[ALL.key.isin(oldk)], label=f'+ 既存銘柄の未採用候補({len(oldk)})', bs=bs)
pfx.ev(T, pfx.BASE9T2, ALL[ALL.key.isin(keys)], label=f'+ 候補すべて({len(keys)})', bs=bs)
for ea in sorted({k.split('@')[0] for k in keys}):
    ks = [k for k in keys if k.startswith(ea + '@')]
    if len(ks) > 1: pfx.ev(T, pfx.BASE9T2, ALL[ALL.key.isin(ks)], label=f'+ {ea} 全部({len(ks)})', bs=bs)
ALL.to_pickle(f'{S}/feat/all_trades_new.pkl')
