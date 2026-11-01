import glob, pandas as pd, numpy as np
from lab import DEV
D = pd.concat([pd.read_pickle(f) for f in glob.glob('x_*.pkl')]); D['grp'] = np.where(D.sym.isin(DEV), '作る側', '確かめる側'); D['t'] = pd.to_datetime(D.t)
D['range'] = D.ncross >= D.groupby('sym').ncross.transform('median')       # more crosses than usual in the last 300 bars = range-like
EX = ['R_tp2', 'R_tp3', 'R_trail', 'R_ma']
print('■ 押し目の回数ごと（1 回の平均 R、作る側／確かめる側）')
for k, g in D.groupby('k'):
    print(f"  {k}回目: " + '  '.join(f"{e[2:]} {g[g.grp=='作る側'][e].mean():+.3f}/{g[g.grp=='確かめる側'][e].mean():+.3f}" for e in EX) + f"   回数 {len(g)}")
print(f"  全部 : " + '  '.join(f"{e[2:]} {D[D.grp=='作る側'][e].mean():+.3f}/{D[D.grp=='確かめる側'][e].mean():+.3f}" for e in EX))
conds = [('broke', '抵抗帯をブレイク'), ('tl_broke', 'TL を上抜け'), ('slope', 'MA75 が上向き'), ('h4', 'H4 も同じ向き'), ('range', 'レンジ寄り（クロス多い）')]
for ex in ('R_tp2', 'R_trail', 'R_ma'):
    print(f'\n■ 条件ごと（出口 {ex[2:]}、あり／なし、作る側｜確かめる側）')
    for c, lab in conds:
        cell = lambda g: f"{g[g[c]][ex].mean():+.3f}×{g[c].sum():4d} / {g[~g[c]][ex].mean():+.3f}×{(~g[c]).sum():4d}"
        print(f"  {lab:16s} {cell(D[D.grp=='作る側'])}  ｜ {cell(D[D.grp=='確かめる側'])}")
D.to_pickle('x_all.pkl')
