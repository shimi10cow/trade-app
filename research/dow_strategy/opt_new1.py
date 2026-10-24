"""New instruments, cheap checks on existing trade files (first-half choice, second-half check):
 (1) J3 grid family robustness; (2) direction only (buy / sell) chosen on the first half for every EA x instrument."""
import glob, os, numpy as np, pandas as pd, new_summary as N
S = N.S; pf = N.pf
def fam(sym, pat):
    out = []
    for p in sorted(glob.glob(f'{S}/ws_{sym}/research/dow_strategy/results/{pat}')):
        x = None if 'summary' in p else N.load(sym, p.split('/results/')[1])
        if x is not None: out.append((os.path.basename(p)[:-4], x))
    return out
print('### J3 の設定違い（前半 PF>=1.15・40回以上で選べるもの → 後半）')
for sym in N.COST:
    F = [(k, x) for k, x in fam(sym, 'turn/j3_*.csv') ]
    st = [(k, pf(x[x.half == 1].R), pf(x[x.half == 2].R), x[x.half == 1].R.sum(), x[x.half == 2].R.sum(), (x.half == 1).sum()) for k, x in F]
    sel = [s for s in st if s[1] >= 1.15 and s[5] >= 40]
    b = max(sel, key=lambda s: s[1]) if sel else None
    print(f'{sym}: {len(st)} 設定、選べる {len(sel)}、後半黒字 {sum(s[2] > 1 for s in sel)}' + (f' | 前半最良 {b[0]} {b[3]:+.0f}R PF{b[1]:.2f} → {b[4]:+.0f}R PF{b[2]:.2f}' if b else ''))
print('\n### 買いだけ／売りだけ（前半で片側の PF が両方より 0.15 以上高く、30 回以上なら採用）')
rows = []
for sym in N.COST:
    for ea, f in N.CORE + [('Q', None), ('PB2', None)]:
        xs = [(f, N.load(sym, f))] if f else []
        for k, x in xs:
            if x is None: continue
            a = x[x.half == 1]; b = x[x.half == 2]; best = ('両方', pf(a.R))
            for s, nm in ((1, '買い'), (-1, '売り')):
                aa = a[a.side == s]
                if len(aa) >= 30 and pf(aa.R) > best[1] + 0.15: best = (nm, pf(aa.R))
            if best[0] != '両方':
                s = 1 if best[0] == '買い' else -1; bb = b[b.side == s]
                rows.append(dict(sym=sym, ea=ea, 片側=best[0], 前半PF両方=pf(a.R), 前半PF片側=best[1], 後半PF両方=pf(b.R), 後半PF片側=pf(bb.R), 後半R両方=b.R.sum(), 後半R片側=bb.R.sum()))
D = pd.DataFrame(rows); print(D.round(2).to_string(index=False))
print(f'\n片側にした {len(D)} 件のうち 後半 PF が上がった {(D.後半PF片側 > D.後半PF両方).sum()} 件、後半でも PF>1 {(D.後半PF片側 > 1).sum()} 件')
