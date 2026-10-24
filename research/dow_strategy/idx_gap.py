"""Index gaps (2026-10-24): XM cash indices trade almost 23 h a day, so gaps appear after the daily break and the weekend.
Gap = first M15 open after a pause of >= 45 min minus the last close before it, in ATR(D1, 20). For |gap| >= 0.2 ATR:
  fill  : price trades back to the pre-gap close within 4 / 24 hours (share)
  drift : close 4 / 24 hours later minus the gap open, in the gap direction (ATR; + = the gap runs on, - = it fades)
by weekend vs daily break, gap up vs down, half. Also gold (weekend only) for comparison."""
import numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SPLIT = {'US30': 2020, 'US500': 2021, 'JP225': 2021, 'XAUUSD': 2015}
rows = []
for sym in SPLIT:
    m = pd.read_csv(f'{S}/ws_{sym}/M15_broker.csv', parse_dates=['time']).set_index('time')
    D = pd.DataFrame(dict(c=m.close.resample('1D').last(), h=m.high.resample('1D').max(), l=m.low.resample('1D').min())).dropna()
    tr = np.maximum(D.h - D.l, np.maximum((D.h - D.c.shift()).abs(), (D.l - D.c.shift()).abs())); atr = tr.rolling(20).mean().shift()
    t = m.index; dt = t.to_series().diff().dt.total_seconds().to_numpy() / 60
    o, c, h, l = (m[z].to_numpy() for z in ('open', 'close', 'high', 'low'))
    for i in np.nonzero(dt >= 45)[0]:
        if i == 0: continue
        a = atr.asof(t[i].normalize()) if t[i].normalize() >= atr.index[0] else np.nan
        if not np.isfinite(a) or a <= 0: continue
        g = (o[i] - c[i - 1]) / a
        if abs(g) < 0.2: continue
        s = np.sign(g); kind = '週末' if dt[i] > 24 * 60 else '毎日の休み'
        out = dict(sym=sym, t=t[i], kind=kind, dir='上の窓' if s > 0 else '下の窓', gap=abs(g), half=1 if t[i].year <= SPLIT[sym] else 2)
        for H in (4, 24):
            j = np.searchsorted(t, t[i] + pd.Timedelta(hours=H)); j = min(j, len(t) - 1)
            seg_l, seg_h = l[i:j + 1], h[i:j + 1]
            out[f'fill{H}'] = bool((seg_l <= c[i - 1]).any()) if s > 0 else bool((seg_h >= c[i - 1]).any())
            out[f'drift{H}'] = s * (c[j] - o[i]) / a
        rows.append(out)
G = pd.DataFrame(rows); G.to_pickle(f'{S}/feat/idx_gap.pkl')
pd.set_option('display.width', 220)
print(G.groupby(['sym', 'kind', 'dir', 'half']).agg(n=('gap', 'size'), 窓の大きさ=('gap', 'median'), 埋め4h=('fill4', 'mean'), 埋め24h=('fill24', 'mean'),
                                                     続き4h=('drift4', 'mean'), 続き24h=('drift24', 'mean')).round(2).to_string())
