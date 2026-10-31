import sys, pandas as pd, numpy as np
d = pd.concat([pd.read_pickle(f'feat_{s}.pkl') for s in sys.argv[1:]]); d['tt'] = pd.to_datetime(d.t)
d['sr_hit'] = d.sr > 0
d['tl_re_hit'] = d.tl_re <= 0.5; d['tl_up_hit'] = d.tl_up <= 0.5
d['h4_late'] = (d.h4 == 'counter') & (d.h4_waves >= 3)
def line(g, mask, lab):
    mid = g.tt.median(); y, n = g[mask], g[~mask]
    f = lambda x: f"{x.R.mean():+.2f}×{len(x)}" if len(x) else '—'
    h = lambda x: f"{x[x.tt<mid].R.mean():+.2f}/{x[x.tt>=mid].R.mean():+.2f}" if len(x) > 1 else ''
    return f"  {lab:22s} あり {f(y)} ({h(y)})  なし {f(n)} ({h(n)})"
for scope, g0 in (('採用分（今の条件）', d[d.adopted]), ('絞り込み前の全部', d)):
    print(f"\n##### {scope}")
    for sym, g in list(g0.groupby('sym')) + [('まとめ', g0)]:
        print(f"== {sym}: {len(g)} 回 平均 {g.R.mean():+.2f}R")
        print(line(g, g.sr_hit, 'H1 レジサポあり'))
        print(line(g, g.tl_re_hit, '抜けた TL に戻り'))
        print(line(g, g.tl_up_hit, '左肩からの上向き TL'))
        print(line(g, g.h4 == 'counter', 'H4 が逆向き（転換狙い）'))
        print(line(g, g.h4_late, 'H4 逆向き 3 波以上'))
