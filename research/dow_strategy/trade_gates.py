"""Attach causal H4 context features to EA trades and look for a gate that is positive in every 5-year block.
Usage: python trade_gates.py results/long_trades_1.csv [Rcol] [timecol]"""
import bisect, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import regime_gate as RG
c = RG._c; A = RG._A; cs = pd.Series(c); C4 = RG._C4
sma1200 = cs.rolling(1200).mean().to_numpy(); sma200 = cs.rolling(200).mean().to_numpy()
er = lambda n: (cs.diff(n).abs() / cs.diff().abs().rolling(n).sum()).to_numpy()
ER60, ER200 = er(60), er(200)
atr_rel = (pd.Series(A) / pd.Series(A).rolling(1500).median()).to_numpy()
trend4 = [b[0] for b in RG._r['bars']]


def attach(tr, tcol='time', side='side'):
    rows = []
    for t, s in zip(pd.to_datetime(tr[tcol]), tr[side]):
        k = bisect.bisect_right(C4, t) - 1
        g20 = RG.regime(t, 20); g40 = RG.regime(t, 40)
        rows.append(dict(side_d200=s * (c[k] - sma1200[k]) / A[k], slope_d200=s * (sma1200[k] - sma1200[k - 30]) / A[k],
                         side_h200=s * (c[k] - sma200[k]) / A[k], er60=ER60[k], er200=ER200[k], atr_rel=atr_rel[k],
                         h4_with=int(trend4[k] == ('up' if s == 1 else 'down')),
                         rev20=g20['REVERSAL'], brk20=g20['BREAKOUT'], rev40=g40['REVERSAL'], brk40=g40['BREAKOUT']))
    return pd.concat([tr.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def blocks(x, R):
    y = pd.to_datetime(x['__t']).dt.year
    out = []
    for a, b in ((2003, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026)):
        m = (y >= a) & (y <= b); out.append((x.loc[m, R].sum(), m.sum()))
    return out


if __name__ == '__main__':
    f = sys.argv[1]; R = sys.argv[2] if len(sys.argv) > 2 else 'Rc'; tcol = sys.argv[3] if len(sys.argv) > 3 else 'time'
    tr = pd.read_csv(f); tr = attach(tr, tcol); tr['__t'] = tr[tcol]
    tr.to_csv(f.replace('.csv', '_ctx.csv'), index=False)
    def show(nm, x):
        b = blocks(x, R)
        print(f'{nm:28s} n={len(x):5d} sum={x[R].sum():+7.1f} avg={x[R].mean():+.3f} | ' + ' '.join(f'{s:+6.1f}({n})' for s, n in b) + f'  min {min(s for s, _ in b):+.1f}')
    show('ALL', tr)
    for fcol in ('side_d200', 'slope_d200', 'side_h200', 'er60', 'er200', 'atr_rel', 'rev20', 'brk20', 'rev40', 'brk40'):
        q = tr[fcol].quantile([1 / 3, 2 / 3]).values
        show(f'{fcol} lo', tr[tr[fcol] <= q[0]]); show(f'{fcol} mid', tr[(tr[fcol] > q[0]) & (tr[fcol] <= q[1])]); show(f'{fcol} hi', tr[tr[fcol] > q[1]])
    show('h4_with=1', tr[tr.h4_with == 1]); show('h4_with=0', tr[tr.h4_with == 0])
