"""Session-to-session behaviour in JST (2026-10-21). Uses the pair's M15 (broker time -> JST). Days = JST calendar days.
  Tokyo  9:00-15:00 range (TH, TL); London 15:00-21:00; NY 21:00-02:00 (+1 day)
  a) London break of the Tokyo range: first side broken (by >= 0.1 x ATR(D)) during London; continuation = close at JST 24:00 vs
     the broken level (ATR(D) units, + = continued); fake = price closes back inside the Tokyo range by 21:00
  b) session returns (close-open, ATR(D)): sign agreement Tokyo->London, London->NY, NY->next Tokyo
  c) London continuation by weekday
Halves 2005-2015 / 2016-2026."""
import sys, os
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
m = pd.read_csv(os.environ['EA_M15_CACHE'], parse_dates=['time'])
t = m.time.dt.tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').dt.tz_convert('Asia/Tokyo').dt.tz_localize(None)
m = m.assign(jt=t).dropna(subset=['jt']); m = m[m.jt >= '2005-01-01'].reset_index(drop=True)
m['d'] = m.jt.dt.normalize(); m['h'] = m.jt.dt.hour + m.jt.dt.minute / 60
dly = m.groupby('d').agg(hi=('high', 'max'), lo=('low', 'min'), cl=('close', 'last'))
pc = dly.cl.shift(1); tr = np.maximum(dly.hi - dly.lo, np.maximum(abs(dly.hi - pc), abs(dly.lo - pc))); atrD = tr.rolling(14).mean().shift(1)
rows = []
G = {d: g for d, g in m.groupby('d')}
days = sorted(G)
for k, d in enumerate(days[:-1]):
    g = G[d]; a = atrD.get(d, np.nan)
    if not np.isfinite(a) or a <= 0: continue
    tk = g[(g.h >= 9) & (g.h < 15)]; ld = g[(g.h >= 15) & (g.h < 21)]; ny1 = g[g.h >= 21]; nd = G.get(days[k + 1])
    if len(tk) < 20 or len(ld) < 20 or nd is None: continue
    ny = pd.concat([ny1, nd[nd.h < 2]]); tk2 = nd[(nd.h >= 9) & (nd.h < 15)]
    TH, TL = tk.high.max(), tk.low.min(); thr = 0.1 * a
    side = 0; lvl = np.nan
    for r in ld.itertuples():
        if r.high > TH + thr: side, lvl = 1, TH; break
        if r.low < TL - thr: side, lvl = -1, TL; break
    end24 = g[g.h < 24].close.iloc[-1]
    rec = dict(d=d, wd=d.weekday(), y=d.year, side=side,
               cont=(side * (end24 - lvl) / a) if side else np.nan,
               fake=(float((ld.close.iloc[-1] <= TH) if side == 1 else (ld.close.iloc[-1] >= TL))) if side else np.nan,
               tok=(tk.close.iloc[-1] - tk.open.iloc[0]) / a, lon=(ld.close.iloc[-1] - ld.open.iloc[0]) / a,
               nyr=((ny.close.iloc[-1] - ny.open.iloc[0]) / a) if len(ny) > 4 else np.nan,
               tok2=((tk2.close.iloc[-1] - tk2.open.iloc[0]) / a) if len(tk2) > 4 else np.nan, trng=(TH - TL) / a)
    rows.append(rec)
D = pd.DataFrame(rows)
def half(x, col, f=np.nanmean):
    return f(x[x.y <= 2015][col]), f(x[x.y >= 2016][col])
B = D[D.side != 0]
print(f'東京レンジ（9-15時）の幅 中央 {D.trng.median():.2f} ATR(D) / ロンドンで抜けた日 {len(B) / len(D):.0%}')
print(f'a) ロンドンで東京レンジを抜けた後 24時までの続き（ATR日足）: 全体 {B.cont.mean():+.3f}  前半/後半 {half(B, "cont")[0]:+.3f}/{half(B, "cont")[1]:+.3f}  だまし率(21時に東京レンジ内) {B.fake.mean():.0%}')
for lo, hi, lab in ((0, 0.5, '東京レンジ狭い(<0.5)'), (0.5, 0.8, '中(0.5-0.8)'), (0.8, 9, '広い(>0.8)')):
    x = B[(B.trng >= lo) & (B.trng < hi)]
    print(f'   {lab}: {len(x)}日 続き {x.cont.mean():+.3f}（{half(x, "cont")[0]:+.3f}/{half(x, "cont")[1]:+.3f}） だまし {x.fake.mean():.0%}')
def agree(a, b):
    x = D[[a, b, 'y']].dropna(); x = x[(x[a].abs() > 0.05) & (x[b].abs() > 0.05)]
    s = np.sign(x[a]) == np.sign(x[b]); return s.mean(), s[x.y <= 2015].mean(), s[x.y >= 2016].mean(), np.corrcoef(x[a], x[b])[0, 1]
for a, b, lab in (('tok', 'lon', '東京→ロンドン'), ('lon', 'nyr', 'ロンドン→NY'), ('nyr', 'tok2', 'NY→翌日東京'), ('tok', 'nyr', '東京→NY')):
    s = agree(a, b); print(f'b) {lab}: 同じ向き {s[0]:.1%}（{s[1]:.1%}/{s[2]:.1%}） 相関 {s[3]:+.3f}')
print('c) 曜日別 ロンドン抜けの続き:', {['月', '火', '水', '木', '金'][w]: f"{x.cont.mean():+.2f}({half(x, 'cont')[0]:+.2f}/{half(x, 'cont')[1]:+.2f})" for w, x in B.groupby('wd') if w < 5})
D.to_csv(Path(os.environ.get('OUTCSV', '/tmp/session2.csv')), index=False)
