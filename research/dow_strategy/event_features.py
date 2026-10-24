"""Which causal features make H4 Dow events (REVERSAL / BREAKOUT) follow through in EVERY 5-year block?
y = signed close move 30 H4 bars later (ATR). Features known at the event bar close."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import regime_gate as RG
h4 = RG._h4; c = RG._c; A = RG._A; H = h4.h.to_numpy(float); L = h4.l.to_numpy(float)
cs = pd.Series(c)
sma200 = cs.rolling(200).mean().to_numpy(); sma1200 = cs.rolling(1200).mean().to_numpy()  # ~ D1 SMA200
er = lambda n: (cs.diff(n).abs() / cs.diff().abs().rolling(n).sum()).to_numpy()
ER60, ER200 = er(60), er(200)
atr_rel = (pd.Series(A) / pd.Series(A).rolling(1500).median()).to_numpy()
rows = []
for e in RG._r['events']:
    if e.get('machine') != 'major' or e['action'] not in ('REVERSAL', 'BREAKOUT'):
        continue
    k = e['idx']
    if k + 30 >= len(c) or k < 1500:
        continue
    s = 1 if (e.get('to') or e['trend']) == 'up' else -1
    prot = e.get('prot_price')
    rows.append(dict(t=RG._C4[k], act=e['action'], y=s * (c[k + 30] - c[k]) / A[k],
                     y10=s * (c[k + 10] - c[k]) / A[k],
                     side_sma200=s * (c[k] - sma200[k]) / A[k], side_d200=s * (c[k] - sma1200[k]) / A[k],
                     slope_d200=s * (sma1200[k] - sma1200[k - 30]) / A[k],
                     er60=ER60[k], er200=ER200[k], atr_rel=atr_rel[k],
                     dist_prot=abs(c[k] - prot) / A[k] if prot else np.nan,
                     mom60=s * (c[k] - c[k - 60]) / A[k], rng20=(H[k-20:k+1].max() - L[k-20:k+1].min()) / A[k]))
d = pd.DataFrame(rows)
d['blk'] = pd.cut(pd.to_datetime(d.t).dt.year, [2002, 2009, 2014, 2019, 2024, 2026], labels=['03-09', '10-14', '15-19', '20-24', '25-26'])
d.to_csv(Path(__file__).parent / 'results' / 'event_features.csv', index=False)
feats = ['side_sma200', 'side_d200', 'slope_d200', 'er60', 'er200', 'atr_rel', 'dist_prot', 'mom60', 'rng20']
for act in ('REVERSAL', 'BREAKOUT'):
    x = d[d.act == act].copy()
    print(f'\n== {act} n={len(x)}  base by block:', ' '.join(f'{b}:{v:+.2f}' for b, v in x.groupby('blk', observed=True).y.mean().items()))
    for f in feats:
        try:
            x['q'] = pd.qcut(x[f], 3, labels=['lo', 'mid', 'hi'])
        except ValueError:
            continue
        t = x.groupby(['q', 'blk'], observed=True).y.mean().unstack()
        line = ' | '.join(f"{q}: " + ' '.join(f'{v:+.2f}' for v in t.loc[q].values) + f"  (min {t.loc[q].min():+.2f})" for q in t.index)
        print(f' {f:12s} {line}')
