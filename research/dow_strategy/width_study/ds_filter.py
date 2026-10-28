import pandas as pd, numpy as np
d = pd.concat([pd.read_pickle(f) for f in ('ds/dsall_trades_US500_JP225.pkl', 'ds/dsall_trades_XAUUSD.pkl')]); d['tt'] = pd.to_datetime(d.t)
h = lambda x: x / pd.Timedelta('1h'); d['W_ln'] = h(d.t_neck - d.t_left); d['W_lr'] = h(d.tt - d.t_left)
a = d[d.adopted]
print('採用分に「左肩→ネック ≥ X 時間」を足した時（合計R・平均R・回数／前半・後半の平均R）')
for col, lab in (('W_ln', '左肩→ネック'), ('W_lr', '左肩→右肩')):
    print(f'-- {lab}')
    for X in (0, 12, 24, 36, 48):
        row = []
        for sym, g in a.groupby('sym'):
            mid = g.tt.median(); k = g[g[col] >= X]; p, q = k[k.tt < mid], k[k.tt >= mid]
            row.append(f"{sym} {k.R.sum():+5.1f}R {k.R.mean():+.2f}×{len(k)} ({p.R.mean():+.2f}/{q.R.mean():+.2f})")
        print(f"  ≥{X:2d}h: " + ' | '.join(row))
