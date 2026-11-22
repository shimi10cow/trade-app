"""Buy / sell pressure per timeframe (2026-11-22, follow-up of study2.py).

For M15 / H1 / H4 / D1 separately: Dow major trend on that timeframe, the current leg, and over the last LOOK bars:
  d_look  estimated delta = sum(v * (2c - h - l) / (h - l)) / sum(v) on M5, signed + = trend direction
  div     the leg's extreme was renewed within the last LOOK bars while d_look < 0 (pressure against the trend)
Outcomes in that timeframe's ATR, in the trend direction: fwd6 / fwd24 bars, ext24 (new leg extreme), rev24 (trend flips).
Position in the leg is controlled the same way as study.py. Samples every LOOK bars.
Also `now(sym)`: the latest state per timeframe (trend, buy / sell share of the last LOOK bars, divergence) -> a table.
Usage: python -m studies.trapped_volume.study3 [SYMBOL ...]   (from research/)"""
import sys

import numpy as np
import pandas as pd

from env_recognition import dow_trend
from env_recognition.pivots import atr
from studies.trapped_volume.study import OUT, load

TFS = {'M15': ('15min', '2019-01-01'), 'H1': ('1h', '2012-01-01'), 'H4': ('4h', '2010-01-01'), 'D1': ('1D', '2005-01-01')}
LOOK = 6


def frame(m, tf):
    rule, since = TFS[tf]
    mm = m[m.t >= pd.Timestamp(since) - pd.Timedelta(days=400 if tf == 'D1' else 60)]
    x = mm.set_index('t').resample(rule, label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last', v='sum')).dropna()
    x = x[x.v > 0].reset_index()
    return mm.reset_index(drop=True), x, pd.Timestamp(since)


def features(m, tf):
    m, x, since = frame(m, tf)
    R = dow_trend.run(x[['t', 'o', 'h', 'l', 'c']], tf)
    tr = np.array([b[0] or '' for b in R['bars']]); n = len(x)
    a = atr(x); C, H, L = (x[z].to_numpy(float) for z in 'chl')
    step = pd.Timedelta(TFS[tf][0])
    ends = np.searchsorted(m.t.to_numpy(), (x.t + step).to_numpy(), side='left'); starts = np.r_[0, ends[:-1]]
    h, l, c, v = (m[z].to_numpy(float) for z in 'hlcv')
    clv = np.where(h > l, (2 * c - h - l) / np.where(h > l, h - l, 1), 0.0)
    cd = np.r_[0, np.cumsum(v * clv)]; cv = np.r_[0, np.cumsum(v)]
    st = np.zeros(n, int)
    for i in range(1, n):
        st[i] = st[i - 1] if tr[i] == tr[i - 1] else i
    return dict(x=x, tr=tr, a=a, C=C, H=H, L=L, ends=ends, starts=starts, cd=cd, cv=cv, st=st, since=since)


def state(F, i):
    """trend sign, leg position, delta of the last LOOK bars (+ = buying), divergence at bar i."""
    tr, C, H, L, st = F['tr'], F['C'], F['H'], F['L'], F['st']
    s = {'up': 1, 'down': -1}.get(tr[i], 0)
    j0, j1 = F['starts'][i - LOOK + 1], F['ends'][i]
    tv = F['cv'][j1] - F['cv'][j0]
    d = (F['cd'][j1] - F['cd'][j0]) / tv if tv > 0 else np.nan
    if not s or i - st[i] < LOOK:
        return s, np.nan, d, 0
    hi, lo = H[st[i]:i + 1].max(), L[st[i]:i + 1].min()
    pos = ((hi - C[i]) if s < 0 else (C[i] - lo)) / max(hi - lo, 1e-12)
    renewed = (L[i - LOOK + 1:i + 1].min() <= lo) if s < 0 else (H[i - LOOK + 1:i + 1].max() >= hi)
    return s, pos, d, int(bool(renewed) and s * d < 0)


def study(sym, tf):
    m = load(sym); F = features(m, tf); x, tr, a, C, H, L, st = F['x'], F['tr'], F['a'], F['C'], F['H'], F['L'], F['st']
    rows = []
    for i in range(130, len(x) - 25, LOOK):
        if x.t.iat[i] < F['since']:
            continue
        s, pos, d, div = state(F, i)
        if not s or np.isnan(pos) or np.isnan(d) or a[i] <= 0:
            continue
        hi, lo = H[st[i]:i + 1].max(), L[st[i]:i + 1].min(); ext = lo if s < 0 else hi
        rows.append(dict(sym=sym, tf=tf, t=x.t.iat[i], s=s, pos=pos, d_look=s * d, div=div,
                         fwd6=s * (C[i + 6] - C[i]) / a[i], fwd24=s * (C[i + 24] - C[i]) / a[i],
                         ext24=bool((L[i + 1:i + 25].min() < ext) if s < 0 else (H[i + 1:i + 25].max() > ext)),
                         rev24=bool((tr[i + 1:i + 25] != tr[i]).any())))
    return pd.DataFrame(rows)


def summary(D):
    out = []
    for (sym, tf), T in D.groupby(['sym', 'tf'], sort=False):
        T = T.copy(); T['pd'] = pd.qcut(T.pos, 10, labels=False, duplicates='drop'); T['y'] = pd.to_datetime(T.t).dt.year
        T['fq'] = T.groupby('pd').d_look.transform(lambda z: pd.qcut(z.rank(method='first'), 3, labels=False))
        top, bot = T[T.fq == 2], T[T.fq == 0]
        dy = top.groupby('y').fwd24.mean() - bot.groupby('y').fwd24.mean()
        dv = T.groupby(['y', 'div']).fwd24.mean().unstack()
        dvy = (dv[1] - dv[0]).dropna() if 1 in dv and 0 in dv else pd.Series(dtype=float)
        g = T.groupby('div').agg(n=('fwd24', 'size'), fwd6=('fwd6', 'mean'), fwd24=('fwd24', 'mean'), ext24=('ext24', 'mean'), rev24=('rev24', 'mean'))
        out.append(dict(銘柄=sym, 時間足=tf, 回数=len(T), 年=T.y.nunique(),
                        デルタ_多マイナス少_fwd24=round(top.fwd24.mean() - bot.fwd24.mean(), 2), デルタ_年でプラス=f'{int((dy > 0).sum())}/{len(dy)}',
                        逆行_回数=int(g.n.get(1, 0)), 逆行_fwd24=round(g.fwd24.get(1, np.nan), 2), 逆行なし_fwd24=round(g.fwd24.get(0, np.nan), 2),
                        逆行_年で悪い=f'{int((dvy < 0).sum())}/{len(dvy)}', 逆行_安値高値更新=round(g.ext24.get(1, np.nan), 2), 逆行なし_更新=round(g.ext24.get(0, np.nan), 2)))
    return pd.DataFrame(out)


def now(sym):
    """the latest closed bar per timeframe: trend, buy share of the last LOOK bars, divergence."""
    m = load(sym); rows = []
    for tf in TFS:
        F = features(m, tf); i = len(F['x']) - 1
        s, pos, d, div = state(F, i)
        buy = (1 + d) / 2 if not np.isnan(d) else np.nan
        rows.append(dict(時間足=tf, 足=str(F['x'].t.iat[i]), トレンド={1: '上', -1: '下'}.get(s, 'なし'),
                         直近の買い割合=f'{buy:.0%}' if buy == buy else '-', 優勢='買い' if d > 0.05 else ('売り' if d < -0.05 else '五分'),
                         波の位置=f'{pos:.2f}' if pos == pos else '-', 逆行='あり' if div else '-'))
    return pd.DataFrame(rows)


if __name__ == '__main__':
    syms = sys.argv[1:] or ['EURUSD', 'USDJPY']
    parts = []
    for s in syms:
        for tf in TFS:
            d = study(s, tf); print(s, tf, len(d), flush=True); parts.append(d)
    D = pd.concat(parts, ignore_index=True); D.to_csv(OUT / 'samples3.csv.gz', index=False)
    S = summary(D); txt = S.to_string(index=False)
    nw = '\n\n'.join(f'## 今の状態 {s}（データの最後の足）\n' + now(s).to_string(index=False) for s in syms)
    (OUT / 'report3.md').write_text('## 時間足ごと（LOOK = 6 本）\n' + txt + '\n\n' + nw, encoding='utf-8'); print(txt); print(nw)
