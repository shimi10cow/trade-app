"""Buy / sell pressure from bars + tick volume (2026-11-22, follow-up of study.py).

Same data and samples as study.py (8 FX, M5 tick volume, 2010-2026, every 6th H4 close). Features, all signed so that
+ = pressure in the H4 Dow trend direction (s = +1 up / -1 down); for the trend-free test, + = buying:
  d_leg   estimated delta over the current leg: sum(v * (2c - h - l) / (h - l)) / sum(v) on M5 (close location x volume)
  d_1d    the same over the last 6 H4 bars (1 day)
  obv_1d  (volume of up M5 bars - volume of down M5 bars) / volume, last 6 H4 bars
  div     price made a new leg extreme within the last 6 H4 bars while d_1d points against the trend (1 / 0)
  absorb  last 6 H4 bars: volume per unit of range vs its 120-bar median (high = much volume, little movement)
  climax  last H4 bar volume / median of the previous 120 H4 bars, only when the bar touched the leg's extreme
Outcomes as study.py (fwd6, fwd24, ext24, rev24) plus, for the trend-free test, raw next 1 / 4 days in ATR (buy side +).
  d_leg_nv the same without volume (plain mean close location), legret = leg move so far in ATR (to see what d_leg adds)
Usage: python -m studies.trapped_volume.study2   (from research/)"""
import numpy as np
import pandas as pd

from env_recognition import dow_trend
from env_recognition.pivots import atr
from studies.trapped_volume.study import OUT, SYMS, load


def study(sym):
    m = load(sym)
    h4 = m.set_index('t').resample('4h', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last', v='sum')).dropna().reset_index()
    R = dow_trend.run(h4[['t', 'o', 'h', 'l', 'c']], 'H4')
    tr = np.array([b[0] or '' for b in R['bars']]); n = len(h4)
    a = atr(h4); C, H, L, V = (h4[z].to_numpy(float) for z in 'chlv')
    rng = np.maximum(H - L, 1e-12)
    m5i = np.searchsorted(m.t.to_numpy(), (h4.t + pd.Timedelta(hours=4)).to_numpy(), side='left'); m5s = np.r_[0, m5i[:-1]]
    h, l, c, o, v = (m[z].to_numpy(float) for z in 'hlcov')
    clv = np.where(h > l, (2 * c - h - l) / np.where(h > l, h - l, 1), 0.0)
    cd = np.r_[0, np.cumsum(v * clv)]; cv = np.r_[0, np.cumsum(v)]; cn = np.r_[0, np.cumsum(clv)]; cu = np.r_[0, np.cumsum(v * np.sign(c - o))]
    def ssum(cs, j0, j1): return cs[j1] - cs[j0]
    vpr = V / rng; vpr_med = pd.Series(vpr).rolling(120, min_periods=60).median().shift(1).to_numpy()
    vmed = pd.Series(V).rolling(120, min_periods=60).median().shift(1).to_numpy()
    start = np.zeros(n, int)
    for i in range(1, n):
        start[i] = start[i - 1] if tr[i] == tr[i - 1] else i
    rows = []
    for i in range(130, n - 25, 6):
        if h4.t.iat[i] < pd.Timestamp('2010-01-01'):
            continue
        s = {'up': 1, 'down': -1}.get(tr[i], 0)
        j1 = m5i[i]; jd = m5s[i - 5]
        tv1 = ssum(cv, jd, j1)
        if tv1 <= 0:
            continue
        d1 = ssum(cd, jd, j1) / tv1; ob1 = ssum(cu, jd, j1) / tv1
        absorb = np.nanmean(vpr[i - 5:i + 1]) / vpr_med[i] if vpr_med[i] > 0 else np.nan
        r = dict(sym=sym, t=h4.t.iat[i], s=s, d1_raw=d1, obv_raw=ob1, absorb=absorb,
                 up6=(C[i + 6] - C[i]) / a[i], up24=(C[i + 24] - C[i]) / a[i])
        if s and i - start[i] >= 6:
            j0 = m5s[start[i]]; tv = ssum(cv, j0, j1)
            hi, lo = H[start[i]:i + 1].max(), L[start[i]:i + 1].min()
            pos = ((hi - C[i]) if s < 0 else (C[i] - lo)) / max(hi - lo, 1e-12)
            ext = lo if s < 0 else hi
            new_ext = (L[i - 5:i + 1].min() <= lo) if s < 0 else (H[i - 5:i + 1].max() >= hi)
            touch = (L[i] <= lo) if s < 0 else (H[i] >= hi)
            fut_ext = (L[i + 1:i + 25].min() < ext) if s < 0 else (H[i + 1:i + 25].max() > ext)
            r.update(pos=pos, d_leg=s * ssum(cd, j0, j1) / tv, d_leg_nv=s * ssum(cn, j0, j1) / max(j1 - j0, 1), legret=s * (C[i] - C[start[i]]) / a[i], d_1d=s * d1, obv_1d=s * ob1,
                     div=int(bool(new_ext) and s * d1 < 0), climax=(V[i] / vmed[i] if touch and vmed[i] > 0 else np.nan),
                     fwd6=s * (C[i + 6] - C[i]) / a[i], fwd24=s * (C[i + 24] - C[i]) / a[i], ext24=bool(fut_ext),
                     rev24=bool((tr[i + 1:i + 25] != tr[i]).any()))
        rows.append(r)
    return pd.DataFrame(rows)


def ctl(T, f, q=3):
    """terciles of feature f inside position deciles -> mean outcomes; plus top - bottom per symbol / per year (sign count)."""
    T = T.dropna(subset=[f]).copy()
    T['pd'] = pd.qcut(T.pos, 10, labels=False, duplicates='drop')
    T['fq'] = T.groupby('pd')[f].transform(lambda x: pd.qcut(x.rank(method='first'), q, labels=False))
    g = T.groupby('fq').agg(n=('fwd24', 'size'), fwd6=('fwd6', 'mean'), fwd24=('fwd24', 'mean'), ext24=('ext24', 'mean'), rev24=('rev24', 'mean')).round(3)
    top, bot = T[T.fq == q - 1], T[T.fq == 0]
    ds = (top.groupby('sym').fwd24.mean() - bot.groupby('sym').fwd24.mean())
    T['y'] = pd.to_datetime(T.t).dt.year
    dy = (top.assign(y=T.y).groupby('y').fwd24.mean() - bot.assign(y=T.y).groupby('y').fwd24.mean())
    return g, f'多−少 fwd24 {top.fwd24.mean() - bot.fwd24.mean():+.3f} ATR / 銘柄でプラス {int((ds > 0).sum())}/{len(ds)} / 年でプラス {int((dy > 0).sum())}/{len(dy)}'


def report(D):
    out = []
    T = D.dropna(subset=['pos'])
    out.append(f'トレンド中のサンプル {len(T):,}（全サンプル {len(D):,}）。fwd24 のばらつき {T.fwd24.std():.2f} ATR。'
               '目安：多−少の差が ±0.15 ATR 未満、または銘柄・年で向きがばらばらなら「効いていない」。')
    for f, name in [('d_leg', '1 推定デルタ（波全体）'), ('d_leg_nv', '1b 終値の位置だけ（出来高なし、波全体）'), ('legret', '参考：波の値幅（ATR）'), ('d_1d', '1 推定デルタ（直近 1 日）'), ('obv_1d', '2 陽線・陰線の出来高（直近 1 日）'),
                    ('absorb', '4 吸収（出来高 / 値幅、直近 1 日）'), ('climax', '5 クライマックス（端に触れた足の出来高倍率）')]:
        g, line = ctl(T, f)
        out.append(f'## {name}（位置をそろえた 3 分位、0 = 少 / 2 = 多、+ はトレンド方向の圧力）\n{g.to_string()}\n{line}')
    x = T.copy(); x['pd'] = pd.qcut(x.pos, 10, labels=False, duplicates='drop')
    g = x.groupby('div').agg(n=('fwd24', 'size'), fwd24=('fwd24', 'mean'), ext24=('ext24', 'mean'), rev24=('rev24', 'mean')).round(3)
    near = x[x.pos > 0.8].groupby('div').agg(n=('fwd24', 'size'), fwd24=('fwd24', 'mean'), ext24=('ext24', 'mean'), rev24=('rev24', 'mean')).round(3)
    out.append(f'## 3 逆行（直近 1 日に波の端を更新したのに、推定デルタが逆向き）\n全部\n{g.to_string()}\n波の端（位置 > 0.8）だけ\n{near.to_string()}')
    # trend-free: does 1-day pressure predict the next 1 / 4 days?
    for f in ['d1_raw', 'obv_raw']:
        z = D.dropna(subset=[f]).copy(); z['q'] = pd.qcut(z[f].rank(method='first'), 5, labels=['1 売り優勢', '2', '3', '4', '5 買い優勢'])
        g = z.groupby('q', observed=True).agg(n=('up24', 'size'), 次の1日=('up6', 'mean'), 次の4日=('up24', 'mean')).round(3)
        out.append(f'## トレンドに関係なく：直近 1 日の {f}（5 分位）→ その後の値動き（ATR、+ = 上）\n{g.to_string()}')
    return '\n\n'.join(out)


if __name__ == '__main__':
    parts = []
    for s in SYMS:
        x = study(s); print(s, len(x), flush=True); parts.append(x)
    D = pd.concat(parts, ignore_index=True); D.to_csv(OUT / 'samples2.csv.gz', index=False)
    r = report(D); (OUT / 'report2.md').write_text(r, encoding='utf-8'); print(r)
