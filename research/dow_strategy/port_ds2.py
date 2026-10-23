"""Adopt the right shoulder (gold + Nikkei, 2R fixed)? DD effect at the SAME fixed risk per trade (2005-2026):
CAGR, max DD, worst year, losing years, trades/year, longest losing streak, max open positions at once,
plus a month-block bootstrap (10-year paths, all years): median / 5% worst DD at that risk; and the correlation of
monthly R between the shoulder and the rest."""
import numpy as np, pandas as pd, combo_stable as CS, port_ds as PD
X0 = pd.concat([PD.base, PD.CJ, PD.M2], ignore_index=True)
DS = pd.concat([PD.ds('XAUUSD'), PD.ds('JP225')], ignore_index=True)
X1 = pd.concat([X0, DS], ignore_index=True)
for X in (X0, X1, DS): X['tt'] = pd.to_datetime(X.tt); X['et'] = pd.to_datetime(X.et)


def streak(r):
    m = c = 0
    for v in r:
        c = c + 1 if v <= 0 else 0; m = max(m, c)
    return m


def maxopen(X):
    ev = pd.concat([pd.Series(1, index=X.tt), pd.Series(-1, index=X.et)]).sort_index(kind='stable')
    return int(ev.cumsum().max())


def boot_dd(X, risk, n=1500, seed=3):
    ms = pd.period_range('2005-01', '2026-09', freq='M')
    byM = {m: g.sort_values('et').R.to_numpy() for m, g in X.groupby(X.et.dt.to_period('M'))}
    seqs = [byM.get(m, np.array([])) for m in ms]; rng = np.random.default_rng(seed); dd = []
    for _ in range(n):
        r = np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 120)]); eq = np.cumprod(1 + risk * r)
        dd.append((eq / np.maximum.accumulate(eq) - 1).min())
    return np.median(dd), np.quantile(dd, 0.05)


rows = []
for lab, X in (('今の候補', X0), ('＋右肩（金・日経）', X1)):
    for risk in (0.005, 0.0075):
        c, dd, y, n = CS.fixed(X, risk); d = X.sort_values('et')
        med, tail = boot_dd(X, risk)
        rows.append(dict(set=lab, risk=f'{risk:.2%}', 年利=f'{c:.1%}', 最大DD=f'{dd:.1%}', 最悪年=f'{y.min():.1%}({y.idxmin()})',
                         マイナス年=f'{(y < 0).sum()}/{len(y)}', 年回数=round(n), 最長連敗=streak(d.R.to_numpy()), 同時保有最大=maxopen(X),
                         DD中央値=f'{med:.1%}', DD悪い方5pct=f'{tail:.1%}'))
pd.set_option('display.width', 250)
print(pd.DataFrame(rows).to_string(index=False))
m0 = X0.groupby(X0.et.dt.to_period('M')).R.sum(); m1 = DS.groupby(DS.et.dt.to_period('M')).R.sum()
j = pd.concat([m0, m1], axis=1).fillna(0); print('\n月ごとの R の相関（候補 vs 右肩）:', round(j.corr().iloc[0, 1], 2))
dd0 = X0.sort_values('et'); eq = np.cumprod(1 + 0.0075 * dd0.R.to_numpy()); u = eq / np.maximum.accumulate(eq) - 1
k = u.argmin(); t_end = dd0.et.iloc[k]; t_start = dd0.et.iloc[np.argmax(eq[:k + 1])]
print(f'候補の最大 DD の期間（0.75%）: {t_start.date()} → {t_end.date()}、その間の右肩: {DS[(DS.et > t_start) & (DS.et <= t_end)].R.sum():+.1f}R（{((DS.et > t_start) & (DS.et <= t_end)).sum()} 回）')
