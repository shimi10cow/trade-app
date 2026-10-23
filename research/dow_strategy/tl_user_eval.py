"""The user's hand-drawn trendlines (2026-10-23: gold 2020 / 2024, USDJPY 2022; H4 / H1 / M15) vs the Dow pivots.
Run inside the instrument's workspace. For each line on its own timeframe:
  anchors  : nearest confirmed pivot of the right kind (lows for a rising line, highs for a falling line) within 3 bars
             of each end; 'consecutive' if no same-kind pivot lies between them, else number skipped
  slope    : per bar in ATR of that timeframe; length in bars
  touches  : bars after the 2nd point whose extreme comes within 0.15 ATR of the line before it breaks
  break    : first CLOSE beyond the line after the 2nd point; then the move over the next 12 / 48 bars of that timeframe
             in the break direction (ATR) and whether the pre-break trend extreme was exceeded again within 48 bars
Also: redraws = later lines whose first point is this line's 2nd point (2->3 redraw) or the same first point (1->3)."""
import os, sys, json, glob
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SYM = os.environ.get('M5_SYM'); src = {'XAUUSD': 'tl_gold', 'USDJPY': 'tl_jpy'}[SYM]
L = pd.DataFrame([json.load(open(f)) for f in glob.glob(f'{S}/{src}/drawings/*.json')])
L = L[(L.kind == 'tl') & (L.created.str.startswith('2026-10-23'))].copy()
L['t1'] = pd.to_datetime(L.t1, unit='s'); L['t2'] = pd.to_datetime(L.t2, unit='s')
sw = L.t1 > L.t2; L.loc[sw, ['t1', 't2', 'p1', 'p2']] = L.loc[sw, ['t2', 't1', 'p2', 'p1']].to_numpy()
conv = (lambda v: np.log(v)) if SYM == 'XAUUSD' else (lambda v: v / 100 if B.c.mean() < 10 else v)
L['p1'] = conv(L.p1.astype(float)); L['p2'] = conv(L.p2.astype(float))
TF = {'M15': (B.m15, B.R15, pd.Timedelta('15min')), 'H1': (B.h1, B.R1, pd.Timedelta('1h')), 'H4': (B.h4, B.R4, pd.Timedelta('4h'))}
rows = []
for x in L.itertuples():
    if x.tf not in TF: continue
    df, R, ln = TF[x.tf]; df = df.reset_index(drop=True); T = pd.DatetimeIndex(pd.to_datetime(df.t)); o, h, l, c = (df[z].to_numpy(float) for z in 'ohlc')
    A = atr(df)
    i1 = T.searchsorted(x.t1); i2 = T.searchsorted(x.t2)
    if i2 >= len(T) - 2 or i1 >= i2: continue
    rising = x.p2 > x.p1; kind = 'lo' if rising else 'hi'
    piv = sorted((e['idx'], e['price']) for e in R['pivot_events'] if e['kind'] == kind)
    pidx = np.array([p[0] for p in piv])
    def near(i):
        k = np.argmin(np.abs(pidx - i)) if len(pidx) else None
        return (pidx[k] if k is not None and abs(pidx[k] - i) <= 3 else None)
    a1, a2 = near(i1), near(i2)
    skipped = int(((pidx > a1) & (pidx < a2)).sum()) if a1 is not None and a2 is not None else None
    a = A[i2] if np.isfinite(A[i2]) else np.nanmedian(A)
    sl = (x.p2 - x.p1) / (i2 - i1); line = lambda i: x.p2 + sl * (i - i2)
    s = 1 if rising else -1
    br = None; touch = 0
    for i in range(i2 + 1, min(len(T), i2 + 2000)):
        if (s == 1 and c[i] < line(i)) or (s == -1 and c[i] > line(i)): br = i; break
        ext = l[i] if s == 1 else h[i]
        if abs(ext - line(i)) <= 0.15 * a: touch += 1
    r = dict(tf=x.tf, year=x.year, rising=rising, slope=abs(sl) / a, length=i2 - i1, anchored1=a1 is not None, anchored2=a2 is not None,
             skipped=skipped, touches=touch, t1=x.t1, t2=x.t2, p1=x.p1, p2=x.p2)
    if br is not None:
        pre_ext = (h[i2:br].max() if s == 1 else l[i2:br].min())
        r.update(bars_to_break=br - i2, brk_t=T[br],
                 mv12=-s * (c[min(br + 12, len(c) - 1)] - c[br]) / a, mv48=-s * (c[min(br + 48, len(c) - 1)] - c[br]) / a,
                 regain48=bool(((h[br + 1:br + 49] > pre_ext) if s == 1 else (l[br + 1:br + 49] < pre_ext)).any()),
                 run_before=(pre_ext - line(br)) * s / a)
    rows.append(r)
D = pd.DataFrame(rows).sort_values(['tf', 't1'])
# redraw relations
D['redraw_23'] = False; D['redraw_13'] = False
for tf, g in D.groupby('tf'):
    for i, x in g.iterrows():
        later = g[(g.t1 > x.t1) & (g.rising == x.rising)]
        if ((later.t1 - x.t2).abs() <= pd.Timedelta('1D')).any() and (abs(later.t1 - x.t2) == abs(later.t1 - x.t2).min()).any(): pass
        D.loc[i, 'redraw_23'] = bool((later.t1 == x.t2).any() | ((later.t1 - x.t2).abs() < pd.Timedelta('2h')).any())
        D.loc[i, 'redraw_13'] = bool(((later.t1 - x.t1).abs() < pd.Timedelta('2h')).any())
pd.set_option('display.width', 240)
print(f'{SYM}: 線 {len(D)} 本')
for tf, g in D.groupby('tf'):
    print(f'\n== {tf}: {len(g)} 本（上昇 {g.rising.sum()}／下降 {(~g.rising).sum()}）')
    print(f'  両端がダウの高安に乗る {((g.anchored1) & (g.anchored2)).mean():.0%}、隣同士（間の飛ばし 0） {(g.skipped == 0).mean():.0%}・1つ飛ばし {(g.skipped == 1).mean():.0%}・2つ以上 {(g.skipped >= 2).mean():.0%}')
    print(f'  傾き（ATR/本）中央 {g.slope.median():.3f}（25% {g.slope.quantile(.25):.3f}・75% {g.slope.quantile(.75):.3f}）、長さ中央 {g.length.median():.0f} 本')
    print(f'  2点目から引き直し（次の線の 1 点目＝この線の 2 点目） {g.redraw_23.mean():.0%}、同じ 1 点目から引き直し {g.redraw_13.mean():.0%}')
    b = g.dropna(subset=['bars_to_break'])
    print(f'  割れた {len(b)} 本：割れるまで中央 {b.bars_to_break.median():.0f} 本、タッチ中央 {b.touches.median():.0f} 回、割れる前に線から離れた距離 中央 {b.run_before.median():.1f}ATR')
    print(f'  割れた後：12本後に割れた方向へ 平均 {b.mv12.mean():+.2f}ATR、48本後 {b.mv48.mean():+.2f}ATR、48本以内に元の高値/安値を更新した割合 {b.regain48.mean():.0%}')
D.to_pickle(f'{S}/feat/tl_user_{SYM}.pkl')
