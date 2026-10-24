"""DD view of the calendar lot multipliers (cal_size.py windows 1 = gold Friday buys, 2 = month start 3 days).
For each variant at fixed risk 0.5 % / 0.75 % per trade (2005-2026): CAGR, max DD, worst year, worst month, longest time
under water (months), bootstrap DD (10-year month-block paths: median / 5 % worst / chance of DD beyond -25 %, -30 %);
and the risk that gives the SAME 5 % worst DD as the base at 0.75 %, with the CAGR at that risk."""
import numpy as np, pandas as pd
src = open(__file__.replace('cal_dd.py', 'cal_size.py')).read().split("pd.set_option('display.width', 220)")[0]
ns = {'__file__': __file__}; exec(src, ns)
X, W, CS = ns['X'], ns['W'], ns['CS']
w1, w2 = W['1 金の金曜（金の買い）'], W['2 月初3日（全EA）']


def var(k1, k2):
    Y = X.copy(); Y.loc[w1, 'R'] *= k1; Y.loc[w2, 'R'] *= k2
    if k1 > 1 and k2 > 1: Y.loc[w1 & w2, 'R'] /= max(k1, k2)          # both windows: use the larger multiplier only
    return Y


ms = pd.period_range('2005-01', '2026-09', freq='M')


def paths(Y, n=1500, seed=3):
    byM = {m: g.sort_values('et').R.to_numpy() for m, g in Y.groupby(Y.et.dt.to_period('M'))}
    seqs = [byM.get(m, np.array([])) for m in ms]; rng = np.random.default_rng(seed)
    return [np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 120)]) for _ in range(n)]


def bstat(P, risk):
    dd = np.array([(lambda e: (e / np.maximum.accumulate(e) - 1).min())(np.cumprod(1 + risk * r)) for r in P])
    fin = np.array([np.prod(1 + risk * r) for r in P])
    return np.median(dd), np.quantile(dd, 0.05), (dd < -0.25).mean(), (dd < -0.30).mean(), np.median(fin) ** 0.1 - 1


def under(Y, risk):
    d = Y.sort_values('et'); eq = pd.Series(np.cumprod(1 + risk * d.R.to_numpy()), index=d.et.to_numpy())
    m = eq.resample('ME').last().ffill(); peak = m.cummax(); uw = (m < peak).astype(int)
    run = best = 0
    for v in uw: run = run + 1 if v else 0; best = max(best, run)
    mon = m.pct_change().min()
    return best, mon


V = {'今の採用（右肩込み）': (1, 1), '金の金曜 ×1.5': (1.5, 1), '月初3日 ×1.5': (1, 1.5), '両方 ×1.5': (1.5, 1.5), '両方 ×2': (2, 2)}
rows = []; P0 = None
for nm, (k1, k2) in V.items():
    Y = var(k1, k2); P = paths(Y)
    for risk in (0.005, 0.0075):
        c, dd, y, n = CS.fixed(Y, risk); bm, b5, p25, p30, g = bstat(P, risk); uw, mon = under(Y, risk)
        rows.append({'組み合わせ': nm, 'リスク': f'{risk:.2%}', '年利': f'{c:.1%}', '最大DD': f'{dd:.1%}', '最悪の年': f'{y.min():+.1%}',
                     '最悪の月': f'{mon:+.1%}', '最長の回復待ち': f'{uw}か月', 'DD中央値': f'{bm:.1%}', 'DD悪い方5%': f'{b5:.1%}',
                     'DD-25%超の確率': f'{p25:.0%}', 'DD-30%超の確率': f'{p30:.0%}'})
    if P0 is None: P0 = P; target = bstat(P0, 0.0075)[1]
    a, b = 0.001, 0.02
    for _ in range(16):
        m = (a + b) / 2
        if bstat(P, m)[1] < target: b = m
        else: a = m
    c, dd, y, n = CS.fixed(Y, a)
    rows.append({'組み合わせ': nm, 'リスク': f'{a:.2%}（DDを基準0.75%と同じに）', '年利': f'{c:.1%}', '最大DD': f'{dd:.1%}', '最悪の年': f'{y.min():+.1%}',
                 '最悪の月': f'{under(Y, a)[1]:+.1%}', '最長の回復待ち': f'{under(Y, a)[0]}か月', 'DD中央値': f'{bstat(P, a)[0]:.1%}', 'DD悪い方5%': f'{bstat(P, a)[1]:.1%}',
                 'DD-25%超の確率': '', 'DD-30%超の確率': ''})
pd.set_option('display.width', 260)
print(pd.DataFrame(rows).to_string(index=False))
