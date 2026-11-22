"""Raw chart pressure -> direction over the next days / weeks (2026-11-22). No Dow, no levels: only M5 bars + tick volume.

One sample per day (the day's last M5 bar). For each look-back window W = 1 day / 5 days / 20 days, from the M5 bars:
  ret     price change over W in daily ATR (what price already did)
  dlt     estimated delta: sum(v * close location) / sum(v), close location = (2c - h - l) / (h - l)   (+ = buyers)
  clv     the same without volume (mean close location)
  obv     (volume of up bars - volume of down bars) / volume
  upfrac  share of M5 bars that closed up
  eff     efficiency: net move / sum of |M5 moves| (signed; 1 = straight line, 0 = back and forth)
  loc     where the close sits in the window's high-low range (0 = at the low, 1 = at the high)
  vabove  share of the window's volume traded above the current close (buyers under water if high)
  vtrend  log(volume of W / average volume of the previous 4 W)
Targets: price change over the next 1 / 5 / 20 days in daily ATR (+ = up).
Tests (years are the independent units, 2010-2026):
  1. rank correlation (IC) per year of each feature with each target: mean, t, years with the same sign
  2. the same after removing what `ret` of the same window explains (does the feature add anything beyond price itself?)
  3. quintile tables for the strongest ones
  4. walk-forward: a ridge model on all features trained on past years only, tested year by year (out of sample)
Usage: python -m studies.trapped_volume.study4 [SYMBOL ...]   (from research/)"""
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

from studies.trapped_volume.study import OUT, load

WIN = {'1d': 1, '5d': 5, '20d': 20}
FEATS = ['ret', 'dlt', 'clv', 'obv', 'upfrac', 'eff', 'loc', 'vabove', 'vtrend']
TGT = {'次1日': 1, '次5日': 5, '次20日': 20}


def build(sym):
    m = load(sym)
    m = m[m.t >= '2009-01-01'].reset_index(drop=True)
    h, l, c, o, v = (m[z].to_numpy(float) for z in 'hlcov')
    clv = np.where(h > l, (2 * c - h - l) / np.where(h > l, h - l, 1), 0.0)
    dc = np.r_[0, np.diff(c)]
    cs = {k: np.r_[0, np.cumsum(a)] for k, a in dict(v=v, vc=v * clv, c=clv, vs=v * np.sign(c - o), up=(c > o).astype(float), n=np.ones_like(c), ad=np.abs(dc)).items()}
    day = m.t.dt.floor('D')
    last = np.flatnonzero(np.r_[day.to_numpy()[1:] != day.to_numpy()[:-1], True])          # last M5 bar of each day
    d = pd.DataFrame(dict(t=day.iloc[last].to_numpy(), j=last))
    d = d[np.r_[0, np.diff(last)] > 50].reset_index(drop=True)                                 # skip thin days (holidays / Sunday stubs)
    D1 = m.groupby(day).agg(h=('h', 'max'), l=('l', 'min'), c=('c', 'last')).loc[d.t].reset_index(drop=True)
    pc = D1.c.shift(1)
    tr = np.maximum(D1.h - D1.l, np.maximum((D1.h - pc).abs(), (D1.l - pc).abs()))
    A = tr.ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    J = d.j.to_numpy(); C = c[J]; rows = {}
    for w, nd in WIN.items():
        j0 = np.r_[np.zeros(nd, int), J[:-nd] + 1] if nd < len(J) else np.zeros(len(J), int)
        S = lambda k: cs[k][J + 1] - cs[k][j0]
        rows[f'ret_{w}'] = (C - c[np.maximum(j0 - 1, 0)]) / A
        rows[f'dlt_{w}'] = S('vc') / S('v')
        rows[f'clv_{w}'] = S('c') / S('n')
        rows[f'obv_{w}'] = S('vs') / S('v')
        rows[f'upfrac_{w}'] = S('up') / S('n')
        rows[f'eff_{w}'] = (C - c[np.maximum(j0 - 1, 0)]) / np.maximum(S('ad'), 1e-12)
        hi = pd.Series(D1.h).rolling(nd, min_periods=1).max().to_numpy(); lo = pd.Series(D1.l).rolling(nd, min_periods=1).min().to_numpy()
        rows[f'loc_{w}'] = (C - lo) / np.maximum(hi - lo, 1e-12)
        va = np.full(len(J), np.nan)
        for k in range(nd, len(J)):
            p = (h[j0[k]:J[k] + 1] + l[j0[k]:J[k] + 1] + c[j0[k]:J[k] + 1]) / 3; vv = v[j0[k]:J[k] + 1]
            if vv.sum() > 0:
                va[k] = vv[p > C[k]].sum() / vv.sum()
        rows[f'vabove_{w}'] = va
        vw = pd.Series(S('v'))
        rows[f'vtrend_{w}'] = np.log(vw / vw.shift(nd).rolling(4).mean())
    for name, nd in TGT.items():
        rows[name] = (pd.Series(C).shift(-nd).to_numpy() - C) / A
    X = pd.DataFrame(rows); X.insert(0, 't', d.t); X.insert(0, 'sym', sym)
    X = X[(X.t >= '2010-01-01')].replace([np.inf, -np.inf], np.nan).reset_index(drop=True)
    return X


def ic_table(X, resid=False):
    X = X.copy(); X['y'] = pd.to_datetime(X.t).dt.year; out = []
    for w in WIN:
        for f in FEATS:
            col = f'{f}_{w}'
            if resid and f == 'ret':
                continue
            for tg in TGT:
                ics = []
                for y, g in X.dropna(subset=[col, tg, f'ret_{w}']).groupby('y'):
                    a = g[col].rank().to_numpy()
                    if resid:                                       # remove the part `ret` of the same window explains
                        r = g[f'ret_{w}'].rank().to_numpy(); a = a - np.polyval(np.polyfit(r, a, 1), r)
                    ics.append(spearmanr(a, g[tg]).statistic)
                ics = np.array(ics); m_, s_ = ics.mean(), ics.std(ddof=1)
                out.append(dict(窓=w, 指標=f, 先=tg, IC平均=round(m_, 3), t=round(m_ / s_ * np.sqrt(len(ics)), 2), 同じ向きの年=f'{int(((ics > 0) == (m_ > 0)).sum())}/{len(ics)}'))
    return pd.DataFrame(out)


def walk_forward(X, tg):
    cols = [f'{f}_{w}' for w in WIN for f in FEATS]
    Z = X.dropna(subset=cols + [tg]).copy(); Z['y'] = pd.to_datetime(Z.t).dt.year; res = []
    gap = TGT[tg]
    for y in range(2014, Z.y.max() + 1):
        tr = Z[Z.y < y].iloc[:-gap] if gap else Z[Z.y < y]; te = Z[Z.y == y]
        if len(te) < 50:
            continue
        mu, sd = tr[cols].mean(), tr[cols].std()
        mdl = Ridge(alpha=10.0).fit((tr[cols] - mu) / sd, tr[tg])
        p = mdl.predict((te[cols] - mu) / sd)
        top = np.abs(p) >= np.quantile(np.abs(p), 0.7)
        res.append(dict(年=y, 回数=len(te), IC=round(spearmanr(p, te[tg]).statistic, 3),
                        向きの的中=round(np.mean(np.sign(p) == np.sign(te[tg])), 3), 自信の高い3割の的中=round(np.mean(np.sign(p[top]) == np.sign(te[tg].to_numpy()[top])), 3)))
    R = pd.DataFrame(res)
    return R, f'{tg}: 年ごとの IC 平均 {R.IC.mean():+.3f}（プラスの年 {int((R.IC > 0).sum())}/{len(R)}）、向きの的中 {R.向きの的中.mean():.1%}、自信の高い 3 割 {R.自信の高い3割の的中.mean():.1%}'


def quint(X, col, tg):
    q = pd.qcut(X[col].rank(method='first'), 5, labels=['1 低', '2', '3', '4', '5 高'])
    return X.groupby(q, observed=True)[tg].agg(['size', 'mean']).round(3).rename(columns={'size': '回数', 'mean': f'{tg}（ATR）'})


if __name__ == '__main__':
    syms = sys.argv[1:] or ['EURUSD', 'USDJPY']
    rep = []
    for s in syms:
        X = build(s); X.to_csv(OUT / f'samples4_{s.lower()}.csv.gz', index=False); print(s, len(X), flush=True)
        T = ic_table(X); Tr = ic_table(X, resid=True)
        strong = T[(T.t.abs() >= 2.5)].sort_values('t', key=abs, ascending=False)
        strong_r = Tr[(Tr.t.abs() >= 2.5)].sort_values('t', key=abs, ascending=False)
        part = [f'# {s}（{len(X):,} 日）', '## 1. そのままの指標で |t| >= 2.5 のもの（IC = 順位の相関、+ なら指標が高いほど上がる）', strong.to_string(index=False) if len(strong) else '（なし）',
                '## 2. 値動き（ret）の分を除いても残るもの |t| >= 2.5', strong_r.to_string(index=False) if len(strong_r) else '（なし）',
                '## 全部の表（そのまま）', T.to_string(index=False)]
        for tg in TGT:
            R, line = walk_forward(X, tg); part += [f'## 4. 過去だけで学習して翌年を予想（{tg}）', line, R.to_string(index=False)]
        for _, r in strong.head(4).iterrows():
            part += [f"## 3. 5 分位 {r.指標}_{r.窓} → {r.先}", quint(X, f'{r.指標}_{r.窓}', r.先).to_string()]
        rep.append('\n\n'.join(part)); print('\n\n'.join(part[:5]), flush=True)
        for tg in TGT:
            print(walk_forward(X, tg)[1], flush=True)
    (OUT / 'report4.md').write_text('\n\n\n'.join(rep), encoding='utf-8')
