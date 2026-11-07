"""Standard results table (user, 2026-11-07): the same items every time.
port(trades) where trades = DataFrame(t, exit_t, R[, w]) -> dict of the standard items."""
import numpy as np
import pandas as pd


def port(p, start, end='2026-10-14', risks=(1.0, 0.5)):
    p = p[(p.t >= start) & (p.exit_t < end)].sort_values('exit_t')
    R = (p.R * p.get('w', 1.0)).to_numpy(float); n = len(R)
    yrs = (pd.Timestamp(end) - pd.Timestamp(start)).days / 365.25
    eq = np.cumsum(R); dd = (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
    ls = mx = 0
    for r in R:
        ls = ls + 1 if r <= 0 else 0; mx = max(mx, ls)
    s = pd.Series(R, index=pd.to_datetime(p.exit_t.values))
    m = s.resample('ME').sum(); y = s.resample('YE').sum()
    w = R[R > 0]; l = R[R <= 0]
    out = {'件数': n, '年あたり件数': round(n / yrs), '勝率': f'{len(w) / n:.0%}', '平均R': f'{R.mean():+.2f}', 'PF': f'{w.sum() / -l.sum():.2f}',
           '合計R': f'{R.sum():+.0f}', '年あたりR': f'{R.sum() / yrs:+.1f}', '最大DD(R)': f'{dd:.1f}', '最大連敗': mx,
           '負けた月の割合': f'{(m < 0).mean():.0%}', '一番悪い年(R)': f'{y.min():+.1f}'}
    for rk in risks:
        simple = R.sum() / yrs * rk
        e = np.cumprod(1 + R * rk / 100); peak = np.maximum.accumulate(np.r_[1, e])[1:]
        cdd = ((peak - e) / peak).max() * 100
        cagr = (e[-1] ** (1 / yrs) - 1) * 100
        out[f'リスク{rk:g}%: 年利(単利)'] = f'{simple:.0f}%'
        out[f'リスク{rk:g}%: 年利(複利)'] = f'{cagr:.0f}%'
        out[f'リスク{rk:g}%: 最大DD'] = f'-{cdd:.1f}%'
    return out
