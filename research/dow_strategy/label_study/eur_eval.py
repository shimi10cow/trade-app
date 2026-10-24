import numpy as np, pandas as pd
from pbcount import *
D = labels('pbm_eur'); print(D.groupby(['tf', 'kind']).size().unstack(fill_value=0)); print(D.dt.min(), D.dt.max())
m = pd.read_csv(f'{S}/EURUSD_M15_long_broker.csv', parse_dates=['time']).set_index('time').loc['2008-06-01':'2009-12-31']
BR = {'H1': bars(m, '1h'), 'H4': bars(m, '4h')}; TT = {k: np.array([int(t.timestamp()) for t in v.index]) for k, v in BR.items()}
for tf in ('H4', 'H1'):
    s, legs = seq(D, tf)
    if not legs: continue
    print(f'\n{tf}: トレンド {len(legs)} 本、押し {(s.k=="N").sum()} 個、平均 {np.mean(legs):.1f}、分布 {pd.Series(legs).value_counts().sort_index().to_dict()}')
    rows = []
    for r in s[s.k == 'N'].itertuples():
        ev = r.t + (6 if tf == 'H1' else 3) * (3600 if tf == 'H1' else 14400)
        rows.append((r.n, {(p, dm): count(BR[tf], TT[tf], r.bt, r.side, ev, p, dm) for p in (2, 3, 4) for dm in (0, 1, 1.5, 2)}))
    out = sorted(((np.mean([min(n, 4) == min(d[g], 4) for n, d in rows]), g, np.mean([abs(min(n, 4) - min(d[g], 4)) <= 1 for n, d in rows])) for g in rows[0][1]), reverse=True)
    fixed = (3, 1) if tf == 'H1' else (2, 1.5)
    fa = [o for o in out if o[1] == fixed][0]
    print(f'  ドル円で決めた設定（前後{fixed[0]}本・ATR×{fixed[1]}）：一致 {fa[0]:.0%}、±1回以内 {fa[2]:.0%}')
    for a, g, w in out[:3]: print(f'  ユーロドルで一番良い設定：前後{g[0]}本・ATR×{g[1]} → 一致 {a:.0%}、±1回以内 {w:.0%}')
    X = pd.DataFrame([(min(n, 4), min(d[fixed], 4)) for n, d in rows], columns=['you', 'auto']); print(pd.crosstab(X.you, X.auto, rownames=['あなた'], colnames=['自動']).to_string())
