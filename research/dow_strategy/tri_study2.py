"""Triangle hypotheses from the user (2026-10-20):
 (1) a break counts once the same-TF Dow turns in the break direction (provisional turn) - avoids early/wick breaks
 (2) only with the higher-TF trend
 (3) after a triangle/wedge the market moves a lot (either way): volatility expansion vs normal times
Outcome measured from the confirmation bar's close (ATR of that TF)."""
import bisect, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import triangles as TR  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
pd.set_option('display.width', 220)
BLK = [2004, 2009, 2014, 2019, 2024, 2026]; LAB = ['05-09', '10-14', '15-19', '20-24', '25-26']
for tf in ('H4', 'H1', 'M15'):
    df, R = TR.FR[tf]; H, L, C = (df[z].to_numpy(float) for z in 'hlc'); A = atr(df); n = len(df); T = pd.to_datetime(df.t)
    hf = TR.HIGHER[tf]; dfh, Rh = TR.FR[hf]; Ch = list(pd.to_datetime(dfh.t) + TF_LEN[hf])
    prov = {d: sorted(e['idx'] for e in R['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START') and e['to'] == d) for d in ('up', 'down')}
    tri = TR.detect2(tf); rows = []
    absmove = np.abs(pd.Series(C).shift(-30) - pd.Series(C)).to_numpy() / A   # unconditional |30-bar move|
    for x in tri:
        if not x['bo'] or T[x['end']].year < 2005:
            continue
        j, s = x['end'], x['bo']; d = 'up' if s == 1 else 'down'
        # (1) first provisional Dow turn in the break direction within 3x the triangle length after the break,
        #     and before price closes back beyond the opposite line
        lst = prov[d]; q = bisect.bisect_left(lst, j); conf = None
        if q < len(lst) and lst[q] <= j + max(10, x['len']):
            conf = lst[q]
        for kind, k in (('抜け', j), ('抜け＋ダウ転換', conf)):
            if k is None or k + 30 >= n:
                continue
            kh = bisect.bisect_right(Ch, T[k] + TF_LEN[tf]) - 1
            seg = slice(k + 1, k + 31)
            rows.append(dict(kind=kind, wedge=x['shape'].startswith('wedge'), year=T[k].year, with_higher=Rh['bars'][kh][0] == d,
                             f30=s * (C[k + 30] - C[k]) / A[k], mfe=s * ((H[seg].max() if s == 1 else L[seg].min()) - C[k]) / A[k],
                             mae=-s * ((L[seg].min() if s == 1 else H[seg].max()) - C[k]) / A[k], absm=abs(C[k + 30] - C[k]) / A[k],
                             base_abs=np.nanmean(absmove[max(0, k - 2000):k])))
    d = pd.DataFrame(rows); d['blk'] = pd.cut(d.year, BLK, labels=LAB)
    print(f'== {tf}  三角 {len(tri)}')
    for kind in ('抜け', '抜け＋ダウ転換'):
        for nm, m in (('全部', True), ('上位足の向き', 'H'), ('上位足の向き・三角', 'HT'), ('上位足の向き・ウェッジ', 'HW'), ('上位足と逆', 'R')):
            x = d[d.kind == kind]
            if m == 'H': x = x[x.with_higher]
            if m == 'HT': x = x[x.with_higher & ~x.wedge]
            if m == 'HW': x = x[x.with_higher & x.wedge]
            if m == 'R': x = x[~x.with_higher]
            g = x.groupby('blk', observed=True).f30.mean()
            print(f'  {kind:8s} {nm:12s} n={len(x):5d} 30本後{x.f30.mean():+.2f} 順行{x.mfe.median():.2f} 逆行{x.mae.median():.2f} | '
                  + ' '.join(f'{b}:{v:+.2f}' for b, v in g.items()) + ('  ★' if len(g) == 5 and (g > 0).all() else ''))
    x = d[d.kind == '抜け']
    print(f'  (3) 抜け後30本の値幅 |動き| {x.absm.mean():.2f} ATR ／ 普段の30本 {x.base_abs.mean():.2f} ATR（比 {x.absm.mean() / x.base_abs.mean():.2f}）')
