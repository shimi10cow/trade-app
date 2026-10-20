"""Combine component EAs (trade files) and report blocks, correlation, compounding at fixed risk."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); from sweep import show
D = Path(__file__).parent / 'results'


def comp(name, f):
    d = pd.read_csv(D / f)
    if 'Rc' in d:
        return pd.DataFrame(dict(src=name, _R=d.Rc, tt=pd.to_datetime(d.time), et=pd.to_datetime(d.ExitTime), side=d.side))
    return pd.DataFrame(dict(src=name, _R=d.R, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t), side=d.side))


def report(parts, risk=(0.01,), start=2005):
    P = pd.concat(parts); P = P[P.tt.dt.year >= start].sort_values('et'); P['_y'] = P.tt.dt.year
    show(P, '+'.join(p.src.iloc[0] for p in parts), P._R == P._R)
    m = P.assign(mo=P.tt.dt.to_period('M')).groupby(['mo', 'src'])._R.sum().unstack().fillna(0)
    print(' 月次相関\n', m.corr().round(2).to_string())
    P['y'] = P.et.dt.year
    for rk in risk:
        eq = 1.; pk = 1; mdd = 0; yr = {}
        for y, g in P.groupby('y'):
            s = eq
            for r in g._R:
                eq *= 1 + rk * r; pk = max(pk, eq); mdd = min(mdd, eq / pk - 1)
            yr[y] = eq / s - 1
        yy = pd.Series(yr)
        print(f' リスク{rk:.1%}: 年平均{eq ** (1 / len(yy)) - 1:.1%} 最大DD{mdd:.1%} 負け年{(yy < 0).sum()}/{len(yy)} 最悪年{yy.min():.1%} 回数/年{len(P) / len(yy):.0f}')
        print(' ', {k: round(v * 100) for k, v in yr.items()})
    return P


if __name__ == '__main__':
    parts = [comp(*a.split('=')) for a in sys.argv[1:]]
    report(parts)
