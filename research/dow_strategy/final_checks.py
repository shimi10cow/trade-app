"""Final checks on feat/final_trades.pkl (final_set.py), 2026-10-24.
 1  whole set: same-risk comparison (pfx.ev) and fixed risk 0.75 % / 1.0 % (+ 'risk halves while >= 10 % below the peak'):
    CAGR, max DD, worst year / month, longest losing streak, max open positions and max open risk (sum of lot multipliers),
    10-year month-block bootstrap DD (median, 5 % worst, chance beyond -30 %); share of R by instrument
 2  period split: each EA's R and the set's CAGR / max DD (1 %) in 2005-09 / 2010-14 / 2015-19 / 2020-22 / 2023-26
 3  cost stress: extra cost (x0.5 / x1.0 / x2.0 of each instrument's base cost per side as a share of price) on every trade"""
import numpy as np, pandas as pd, pfx
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
X = pd.read_pickle(f'{S}/feat/final_trades.pkl')
BASE = {'EURUSD': 1.2e-4 / 1.116, 'USDJPY': 1.5e-2 / 158.5, 'XAUUSD': 2.5e-4, 'XAGUSD': 5e-4, 'US30': 1e-4, 'US500': 0.8 / 7670, 'JP225': 10 / 62500, 'BTCUSD': 8e-4}
pd.set_option('display.width', 230)


def path(Y, risk, rule=False):
    d = Y.sort_values('et'); eq = 1.0; pk = 1.0; out = []
    for r in d.Rm.to_numpy():
        k = 0.5 if rule and eq < 0.9 * pk else 1.0
        eq *= 1 + risk * k * r; pk = max(pk, eq); out.append(eq)
    return pd.Series(out, index=d.et.to_numpy())


def stats(Y, risk, rule=False):
    e = path(Y, risk, rule); yrs = (e.index[-1] - e.index[0]).days / 365.25
    dd = (e / e.cummax() - 1).min(); ye = e.resample('YE').last(); yr = ye.pct_change(); yr.iloc[0] = ye.iloc[0] - 1
    mo = e.resample('ME').last().ffill().pct_change().min()
    return e.iloc[-1] ** (1 / yrs) - 1, dd, yr.min(), mo


def boot(Y, risk, rule=False, n=800, seed=5):
    ms = pd.period_range('2005-01', '2026-09', freq='M')
    byM = {m: g.sort_values('et').Rm.to_numpy() for m, g in Y.groupby(Y.et.dt.to_period('M'))}
    seqs = [byM.get(m, np.array([])) for m in ms]; rng = np.random.default_rng(seed); dds = []
    for _ in range(n):
        r = np.concatenate([seqs[i] for i in rng.integers(0, len(seqs), 120)]); eq = 1.0; pk = 1.0; mdd = 0.0
        for v in r:
            k = 0.5 if rule and eq < 0.9 * pk else 1.0
            eq *= 1 + risk * k * v; pk = max(pk, eq); mdd = min(mdd, eq / pk - 1)
        dds.append(mdd)
    dds = np.array(dds); return np.median(dds), np.quantile(dds, 0.05), (dds < -0.3).mean()


def streak(r):
    m = c = 0
    for v in r: c = c + 1 if v <= 0 else 0; m = max(m, c)
    return m


def openrisk(Y):
    ev = pd.concat([pd.Series(Y.mult.to_numpy() * Y.wt.to_numpy(), index=Y.tt.to_numpy()), pd.Series(-Y.mult.to_numpy() * Y.wt.to_numpy(), index=Y.et.to_numpy())]).sort_index(kind='stable')
    cnt = pd.concat([pd.Series(1, index=Y.tt.to_numpy()), pd.Series(-1, index=Y.et.to_numpy())]).sort_index(kind='stable')
    return int(cnt.cumsum().max()), ev.cumsum().max(), cnt.cumsum().quantile(0.99)


keys = list(X.key.unique())
print('######## 1. 最終セット全体')
pfx.ev(X.assign(R=X.R0), keys, label='補正前（今まで）')
pfx.ev(X.assign(R=X.R), keys, label='補正後（スワップ・入った足）')
pfx.ev(X.assign(R=X.Rm), keys, label='補正後＋暦のロット1.5倍')
rows = []
for risk in (0.0075, 0.01):
    for rule in (False, True):
        c, dd, wy, wm = stats(X, risk, rule); bm, b5, p30 = boot(X, risk, rule)
        rows.append({'リスク': f'{risk:.2%}', 'DD10%で半分': 'あり' if rule else 'なし', '年利': f'{c:.1%}', '最大DD': f'{dd:.1%}', '最悪の年': f'{wy:+.1%}',
                     '最悪の月': f'{wm:+.1%}', 'DD中央(10年)': f'{bm:.1%}', 'DD悪い方5%': f'{b5:.1%}', '-30%超': f'{p30:.0%}'})
print(pd.DataFrame(rows).to_string(index=False))
mx, mr, q99 = openrisk(X)
print(f'年 {len(X) / 21.8:.0f} 回、最長連敗 {streak(X.sort_values("et").Rm.to_numpy())}、同時に持つ最大 {mx}（99% の時点で {q99:.0f} 以下）、同時のリスクの合計の最大 {mr:.1f} 回分')
sh = X.groupby('pair').Rm.sum(); print('銘柄ごとの R の割合', (sh / sh.sum()).round(2).sort_values(ascending=False).to_dict())
print('\n######## 2. 期間ごと')
P = pd.cut(X.tt.dt.year, [2004, 2009, 2014, 2019, 2022, 2026], labels=['05-09', '10-14', '15-19', '20-22', '23-26'])
t = X.assign(P=P).pivot_table(index='key', columns='P', values='Rm', aggfunc='sum', observed=False).round(1)
t['負けた期間'] = (t < 0).sum(axis=1); print(t.to_string())
for lab in ['05-09', '10-14', '15-19', '20-22', '23-26']:
    Y = X[P == lab]
    c, dd, wy, wm = stats(Y, 0.01, True); print(f'  {lab}: 1%＋半分ルール 年利 {c:.1%} 最大DD {dd:.1%} 最悪の年 {wy:+.1%}（{len(Y)} 回）')
print('\n######## 3. コストを厳しく（片道あたりのコストを足す）')
for k in (0.5, 1.0, 2.0):
    extra = np.array([2 * k * BASE[p] for p in X.pair]) / X.w.fillna(X.w.median()).to_numpy() * X.wt.to_numpy() * X.mult.to_numpy()
    Y = X.assign(Rm=X.Rm - extra)
    pfx.ev(Y.assign(R=Y.Rm), keys, label=f'コスト +{k:.0%}（往復で基準の {2 * k:.0f} 倍分を追加）')
    c, dd, wy, wm = stats(Y, 0.01, True)
    by = Y.groupby('key').Rm.sum().round(0)
    print(f'    1%＋半分ルール 年利 {c:.1%} 最大DD {dd:.1%} | マイナスになる EA: {list(by[by < 0].index)} | EA別 {by.to_dict()}')
