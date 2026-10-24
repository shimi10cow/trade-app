import sys, numpy as np, pandas as pd
sys.path.insert(0, '..')
from pfx import ev, BASE9T2
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
A = pd.read_pickle(f'{S}/feat/pbstate_all.pkl')
def judge(name, skip):
    rows = []
    for k, g in A.groupby('key'):
        m = skip.loc[g.index]; rows.append((k, g.adopted.iat[0], -g.R[m & (g.half == 1)].sum(), -g.R[m & (g.half == 2)].sum(), m.mean()))
    r = pd.DataFrame(rows, columns=['key', 'ad', 'd1', 'd2', 'skip']); a = r[r.ad]
    print(f'{name:34s} 外す{r.skip.mean():4.0%} 全EA {r.d1.sum():+7.1f}/{r.d2.sum():+7.1f} 両方改善{((r.d1>0)&(r.d2>0)).sum():2d} 両方悪化{((r.d1<0)&(r.d2<0)).sum():2d} | 採用 {a.d1.sum():+6.1f}/{a.d2.sum():+6.1f} 両方改善 {((a.d1>0)&(a.d2>0)).sum()}/{len(a)}', flush=True)
    return r
h1b = (A.H1_dir > 0) & (A.H1_cnt == 0); h4b = (A.H4_dir > 0) & (A.H4_cnt == 0); h44 = (A.H4_dir > 0) & (A.H4_cnt >= 4)
r1 = judge('H1 B〜1回目なら入らない', h1b)
r2 = judge('H4 B〜1回目なら入らない', h4b)
r3 = judge('H1 か H4 が B〜1回目なら入らない', h1b | h4b)
r4 = judge('H4 4回目以降なら入らない', h44)
r5 = judge('H4 4回目以降（戻り型だけ）', h44 & ~A.pair.isin(['USDJPY', 'XAUUSD', 'BTCUSD']))
print(r1[r1.ad].round(1).to_string(index=False))
print(r2[r2.ad].round(1).to_string(index=False))
ev(A, BASE9T2, label='9本T2（基準）')
for lab, m in (('H1 B〜1回目を外す', h1b), ('H4 B〜1回目を外す', h4b), ('H1かH4 B〜1回目を外す', h1b | h4b)):
    B = A[~m]; ev(B, BASE9T2, label=lab)
