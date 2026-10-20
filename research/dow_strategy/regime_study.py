"""Does the regime measure predict the next H4 event's follow-through? (persistence test, by 5-year block)"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import regime_gate as RG
rows = []
for e in RG._r['events']:
    if e.get('machine') != 'major' or e['action'] not in ('REVERSAL', 'BREAKOUT'):
        continue
    k = e['idx']
    if k + RG.HZ >= len(RG._c):
        continue
    s = 1 if (e.get('to') or e['trend']) == 'up' else -1
    t = RG._C4[k]
    r = dict(t=t, act=e['action'], y=s * (RG._c[k + RG.HZ] - RG._c[k]) / RG._A[k])
    for N in (10, 20, 40, 80):
        g = RG.regime(t, N); r[f'rev{N}'] = g['REVERSAL']; r[f'brk{N}'] = g['BREAKOUT']
    rows.append(r)
d = pd.DataFrame(rows); d['blk'] = pd.cut(pd.to_datetime(d.t).dt.year, [2002, 2009, 2014, 2019, 2024, 2026], labels=['03-09', '10-14', '15-19', '20-24', '25-26'])
d.to_csv(Path(__file__).parent / 'results' / 'regime_study.csv', index=False)
pd.set_option('display.width', 200)
for act, key in (('REVERSAL', 'rev'), ('BREAKOUT', 'brk')):
    x = d[d.act == act]
    print('==', act, 'mean y by block:', x.groupby('blk', observed=True).y.mean().round(2).to_dict())
    for N in (10, 20, 40, 80):
        g = x[f'{key}{N}']
        on = x[g > 0].groupby('blk', observed=True).y.agg(['mean', 'size']).round(2)
        off = x[g <= 0].groupby('blk', observed=True).y.agg(['mean', 'size']).round(2)
        print(f' N={N} gate>0:', ' '.join(f"{b}:{r['mean']:+.2f}({int(r['size'])})" for b, r in on.iterrows()))
        print(f'       gate<=0:', ' '.join(f"{b}:{r['mean']:+.2f}({int(r['size'])})" for b, r in off.iterrows()))
    # cross: does the OTHER kind's regime predict? (rev regime negative => breakouts work?)
    other = 'brk' if key == 'rev' else 'rev'
    for N in (20, 40):
        g = x[f'{key}{N}'] - x[f'{other}{N}']
        on = x[g > 0].groupby('blk', observed=True).y.agg(['mean', 'size']).round(2)
        print(f' diff N={N} >0:', ' '.join(f"{b}:{r['mean']:+.2f}({int(r['size'])})" for b, r in on.iterrows()))
