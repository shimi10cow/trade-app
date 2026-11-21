"""Trapped-side volume study (2026-11-22).

Question (trader): in an H4 Dow downtrend, if a lot of volume traded ABOVE the current price during the current leg
(= many buyers now under water), does price keep falling (their stops add fuel)? Mirror for uptrends.

Per symbol (M5 with tick volume, 2010-2026):
  H4 bars (resampled M5), Dow major trend per bar (env_recognition.dow_trend). Leg = bars since the trend started.
  Sample every 6th H4 close inside a trend with a leg of >= 6 bars.
  trap_v = share of the leg's M5 tick volume traded on the losing side of the current close (above for down, below for up)
  trap_t = same share counted in M5 bars (time), so trap_v - trap_t = what volume adds beyond "where price spent time"
  pos    = where the close is in the leg's range (1 = at the leg's extreme in the trend direction)
Outcomes (in trend direction, H4 ATR units): fwd6 (1 day), fwd24 (4 days); ext24 = new leg extreme within 24 bars;
  rev24 = major trend reversed within 24 bars.
Usage: python -m studies.trapped_volume.study   (from research/)"""
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'research'))
from env_recognition import dow_trend  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402

OUT = Path(__file__).with_name('results'); OUT.mkdir(exist_ok=True)
SYMS = {'EURUSD': 'research/datasets/raw/m5/EURUSD_M5.csv.gz', 'USDJPY': 'research/datasets/raw/m5/USDJPY_M5.csv.gz',
        'GBPUSD': 'GBPUSD2003.M5.zip', 'USDCAD': 'USDCAD2003.M5.zip', 'USDCHF': 'USDCHF2003.M5.zip',
        'EURJPY': 'EURJPY2003.M5.zip', 'CADJPY': 'CADJPY2003.M5.zip', 'CHFJPY': 'CHFJPY2003.M5.zip'}
START = '2009-01-01'


def load(sym):
    f = ROOT / SYMS[sym]
    if f.suffix == '.zip':
        z = zipfile.ZipFile(f); d = pd.read_csv(z.open(z.namelist()[0]))
        d['t'] = pd.to_datetime(d['<DTYYYYMMDD>'].astype(str) + d['<TIME>'].astype(str).str.zfill(4), format='%Y%m%d%H%M')
        d = d.rename(columns={'<OPEN>': 'o', '<HIGH>': 'h', '<LOW>': 'l', '<CLOSE>': 'c', '<VOL>': 'v'})
    else:
        d = pd.read_csv(f, usecols=['time', 'open', 'high', 'low', 'close', 'tick_volume'])
        d = d.rename(columns={'time': 't', 'open': 'o', 'high': 'h', 'low': 'l', 'close': 'c', 'tick_volume': 'v'}); d['t'] = pd.to_datetime(d.t)
    d = d[d.t >= START][['t', 'o', 'h', 'l', 'c', 'v']].sort_values('t').reset_index(drop=True)
    return d


def study(sym):
    m = load(sym)
    h4 = m.set_index('t').resample('4h', label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last', v='sum')).dropna().reset_index()
    R = dow_trend.run(h4[['t', 'o', 'h', 'l', 'c']], 'H4')
    tr = np.array([b[0] or '' for b in R['bars']]); n = len(h4)
    a = atr(h4); C = h4.c.to_numpy(); H = h4.h.to_numpy(); L = h4.l.to_numpy()
    # M5 index range per H4 bar
    h4end = (h4.t + pd.Timedelta(hours=4)).to_numpy()
    m5i = np.searchsorted(m.t.to_numpy(), h4end, side='left')          # M5 bars of H4 bar i: [m5i[i-1], m5i[i])
    m5s = np.r_[0, m5i[:-1]]
    tp = ((m.h + m.l + m.c) / 3).to_numpy(); v = m.v.to_numpy(float)
    start = np.zeros(n, int)
    for i in range(1, n):
        start[i] = start[i - 1] if tr[i] == tr[i - 1] else i
    rows = []
    for i in range(60, n - 25, 6):
        s = {'up': 1, 'down': -1}.get(tr[i], 0)
        if not s or i - start[i] < 6 or h4.t.iat[i] < pd.Timestamp('2010-01-01'):
            continue
        j0, j1 = m5s[start[i]], m5i[i]
        p, w = tp[j0:j1], v[j0:j1]
        if w.sum() <= 0:
            continue
        lose = (p > C[i]) if s < 0 else (p < C[i])
        hi, lo = H[start[i]:i + 1].max(), L[start[i]:i + 1].min()
        pos = ((hi - C[i]) if s < 0 else (C[i] - lo)) / max(hi - lo, 1e-12)
        ext_lvl = lo if s < 0 else hi
        fut_ext = (L[i + 1:i + 25].min() < ext_lvl) if s < 0 else (H[i + 1:i + 25].max() > ext_lvl)
        rows.append(dict(sym=sym, t=h4.t.iat[i], s=s, leg=i - start[i], trap_v=w[lose].sum() / w.sum(), trap_t=lose.mean(), pos=pos,
                         fwd6=s * (C[i + 6] - C[i]) / a[i], fwd24=s * (C[i + 24] - C[i]) / a[i], ext24=bool(fut_ext),
                         rev24=bool((tr[i + 1:i + 25] != tr[i]).any())))
    return pd.DataFrame(rows)


def report(D):
    D = D.copy(); D['excess'] = D.trap_v - D.trap_t
    out = []
    def tab(g, by):
        x = g.groupby(by, observed=True).agg(n=('fwd24', 'size'), fwd6=('fwd6', 'mean'), fwd24=('fwd24', 'mean'), ext24=('ext24', 'mean'), rev24=('rev24', 'mean'))
        return x.round(3)
    D['trap_q'] = pd.qcut(D.trap_v, 5, labels=['1 少', '2', '3', '4', '5 多'])
    out.append('## 捕まった側の出来高の割合（5 分位）全体\n' + tab(D, 'trap_q').to_string())
    D['pos_b'] = pd.cut(D.pos, [-0.01, 0.5, 0.8, 1.01], labels=['波の途中(<0.5)', '伸びの近く(0.5-0.8)', '端(>0.8)'])
    D['tq3'] = D.groupby('pos_b', observed=True).trap_v.transform(lambda x: pd.qcut(x, 3, labels=False, duplicates='drop'))
    out.append('## 位置をそろえて（各位置の中で 3 分位、0 = 少 / 2 = 多）\n' + tab(D, ['pos_b', 'tq3']).to_string())
    D['xq3'] = D.groupby('pos_b', observed=True).excess.transform(lambda x: pd.qcut(x, 3, labels=False, duplicates='drop'))
    out.append('## 出来高だけの上乗せ（出来高の割合 − 時間の割合、位置ごとの 3 分位）\n' + tab(D, ['pos_b', 'xq3']).to_string())
    # per symbol / period: fwd24 of top vs bottom trap tercile within position buckets
    D['period'] = np.where(D.t < '2018-01-01', '2010-17', '2018-26')
    g = D.groupby(['sym']).apply(lambda x: pd.Series({'多-少 fwd24': x[x.tq3 == 2].fwd24.mean() - x[x.tq3 == 0].fwd24.mean(),
                                                       '多-少 ext24': x[x.tq3 == 2].ext24.mean() - x[x.tq3 == 0].ext24.mean(),
                                                       '上乗せ 多-少 fwd24': x[x.xq3 == 2].fwd24.mean() - x[x.xq3 == 0].fwd24.mean()}), include_groups=False)
    out.append('## 銘柄ごと（位置をそろえた 3 分位の 多 − 少）\n' + g.round(3).to_string())
    g2 = D.groupby(['period', 's']).apply(lambda x: pd.Series({'n': len(x), '多-少 fwd24': x[x.tq3 == 2].fwd24.mean() - x[x.tq3 == 0].fwd24.mean(),
                                                               '上乗せ 多-少 fwd24': x[x.xq3 == 2].fwd24.mean() - x[x.xq3 == 0].fwd24.mean()}), include_groups=False)
    out.append('## 期間・向きごと（s=-1 下げ, 1 上げ）\n' + g2.round(3).to_string())
    return '\n\n'.join(out)


if __name__ == '__main__':
    parts = []
    for s in SYMS:
        x = study(s); print(s, len(x), flush=True); parts.append(x)
    D = pd.concat(parts, ignore_index=True); D.to_csv(OUT / 'samples.csv.gz', index=False)
    r = report(D); (OUT / 'report.md').write_text(r, encoding='utf-8'); print(r)
