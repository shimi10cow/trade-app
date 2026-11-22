"""COT (CFTC Commitments of Traders) positioning -> currency direction over the next weeks (2026-11-22).

Data: CFTC public history files (free), www.cftc.gov/files/dea/history/
  legacy   deacot{YYYY}.zip  2003-2026: noncommercial (large speculators), commercial (hedgers), nonreportable (small traders)
  TFF      fut_fin_txt_{YYYY}.zip 2010-2026: leveraged funds, asset managers, dealers
  Only the 5 CME currency futures with price data here are kept (cot_fx.csv, written by `extract`).
Prices: M5 files of study.py (EURUSD, USDJPY, GBPUSD, USDCAD, USDCHF).
Timing (no look-ahead): positions are as of Tuesday and published Friday; the trade price is the first M5 close of the
  following Monday (report date + 6 days). Returns are for the CURRENCY of the future (JPY / CAD / CHF up = USDxxx down).
Features (net = (long - short) / open interest):
  nc  large speculators net, sm small traders net, cm commercials net, lev leveraged funds net, am asset managers net (TFF)
  *_idx  where the net sits in its own last 156 weeks (0 = lowest, 1 = highest; the usual "COT index")
  *_chg4 change of the net over 4 weeks;  mom13 = currency return over the previous 13 weeks (positions follow price)
Targets: currency return over the next 4 / 8 / 13 weeks in units of its weekly volatility (52-week sd).
Usage: python -m studies.cot.study extract <dir with the zips>   |   python -m studies.cot.study"""
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from studies.trapped_volume.study import load

HERE = Path(__file__).parent; OUT = HERE / 'results'; OUT.mkdir(exist_ok=True)
CODES = {'099741': ('EUR', 'EURUSD', 1), '097741': ('JPY', 'USDJPY', -1), '096742': ('GBP', 'GBPUSD', 1),
         '090741': ('CAD', 'USDCAD', -1), '092741': ('CHF', 'USDCHF', -1)}


def extract(src):
    src = Path(src); L = []; F = []
    for f in sorted(src.glob('deacot*.zip')):
        z = zipfile.ZipFile(f); d = pd.read_csv(z.open(z.namelist()[0]), low_memory=False, dtype={'CFTC Contract Market Code': str})
        d = d[d['CFTC Contract Market Code'].str.strip().isin(CODES)]
        L.append(pd.DataFrame(dict(code=d['CFTC Contract Market Code'].str.strip(), date=pd.to_datetime(d['As of Date in Form YYYY-MM-DD']),
                                   oi=d['Open Interest (All)'], nc_l=d['Noncommercial Positions-Long (All)'], nc_s=d['Noncommercial Positions-Short (All)'],
                                   cm_l=d['Commercial Positions-Long (All)'], cm_s=d['Commercial Positions-Short (All)'],
                                   sm_l=d['Nonreportable Positions-Long (All)'], sm_s=d['Nonreportable Positions-Short (All)'])))
    for f in sorted(src.glob('fin*.zip')):
        z = zipfile.ZipFile(f); d = pd.read_csv(z.open(z.namelist()[0]), low_memory=False, dtype={'CFTC_Contract_Market_Code': str})
        d = d[d['CFTC_Contract_Market_Code'].str.strip().isin(CODES)]
        F.append(pd.DataFrame(dict(code=d['CFTC_Contract_Market_Code'].str.strip(), date=pd.to_datetime(d['As_of_Date_In_Form_YYMMDD'].astype(str).str.zfill(6), format='%y%m%d'),
                                   lev_l=d['Lev_Money_Positions_Long_All'], lev_s=d['Lev_Money_Positions_Short_All'],
                                   am_l=d['Asset_Mgr_Positions_Long_All'], am_s=d['Asset_Mgr_Positions_Short_All'])))
    L = pd.concat(L).drop_duplicates(['code', 'date']); F = pd.concat(F).drop_duplicates(['code', 'date'])
    X = L.merge(F, on=['code', 'date'], how='left').sort_values(['code', 'date'])
    X['cur'] = X.code.map(lambda c: CODES[c][0]); X.to_csv(HERE / 'cot_fx.csv', index=False)
    print(X.groupby('cur').date.agg(['min', 'max', 'size']))


def weekly_price(pair, dates):
    import studies.trapped_volume.study as base
    base.START = '2003-01-01'                                  # the M5 loader starts in 2009 by default: read everything here
    m = load(pair); t = m.t.to_numpy(); c = m.c.to_numpy()
    want = (pd.to_datetime(dates) + pd.Timedelta(days=6)).to_numpy()
    j = np.searchsorted(t, want)                               # first M5 bar from Monday 00:00
    ok = (j < len(t)) & (want >= t[0])
    ok[ok] &= (t[j[ok]] - want[ok]) < np.timedelta64(4, 'D')  # no price within 4 days -> missing, never a stale one
    p = np.full(len(dates), np.nan); p[ok] = c[j[ok]]
    return p


def panel():
    X = pd.read_csv(HERE / 'cot_fx.csv', parse_dates=['date'], dtype={'code': str}); out = []
    for code, g in X.groupby('code'):
        cur, pair, sgn = CODES[code]; g = g.sort_values('date').reset_index(drop=True)
        g['px'] = weekly_price(pair, g.date)
        r = sgn * np.log(g.px).diff()                                   # weekly currency return
        vol = r.rolling(52, min_periods=26).std().shift(1)
        for k in ['nc', 'sm', 'cm', 'lev', 'am']:
            g[k] = (g[f'{k}_l'] - g[f'{k}_s']) / g.oi
            g[f'{k}_idx'] = g[k].rolling(156, min_periods=104).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)
            g[f'{k}_chg4'] = g[k] - g[k].shift(4)
        g['mom13'] = r.rolling(13).sum() / (vol * np.sqrt(13))
        lp = sgn * np.log(g.px)
        for h in (4, 8, 13):
            g[f'f{h}'] = (lp.shift(-h) - lp) / (vol * np.sqrt(h))
        g['cur'] = cur; out.append(g)
    P = pd.concat(out, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    for h in ('f4', 'f8', 'f13'):
        P.loc[P[h].abs() > 10, h] = np.nan                     # price gaps in the M5 files (missing / frozen weeks)
    return P[P.date >= '2004-01-01']


FEATS = ['nc', 'nc_idx', 'nc_chg4', 'sm', 'sm_idx', 'sm_chg4', 'cm_idx', 'lev', 'lev_idx', 'lev_chg4', 'am', 'am_idx', 'am_chg4', 'mom13']


def ic(P, resid=False):
    P = P.copy(); P['y'] = P.date.dt.year; rows = []
    for f in FEATS:
        if resid and f == 'mom13':
            continue
        for h in ('f4', 'f8', 'f13'):
            v = []
            for y, g in P.dropna(subset=[f, h, 'mom13']).groupby('y'):
                if len(g) < 40:
                    continue
                a = g[f].rank().to_numpy()
                if resid:
                    r = g['mom13'].rank().to_numpy(); a = a - np.polyval(np.polyfit(r, a, 1), r)
                v.append(spearmanr(a, g[h]).statistic)
            v = np.array(v); m_ = v.mean()
            percur = P.dropna(subset=[f, h]).groupby('cur').apply(lambda g: spearmanr(g[f], g[h]).statistic, include_groups=False)
            rows.append(dict(指標=f, 先={'f4': '4週', 'f8': '8週', 'f13': '13週'}[h], IC=round(m_, 3), t=round(m_ / v.std(ddof=1) * np.sqrt(len(v)), 2),
                             同じ向きの年=f'{int(((v > 0) == (m_ > 0)).sum())}/{len(v)}', 同じ向きの通貨=f'{int(((percur > 0) == (m_ > 0)).sum())}/{len(percur)}'))
    return pd.DataFrame(rows)


def extremes(P, f, h):
    g = P.dropna(subset=[f, h])
    b = pd.cut(g[f], [-0.01, 0.1, 0.3, 0.7, 0.9, 1.01], labels=['0-10%（極端に売り越し）', '10-30%', '30-70%', '70-90%', '90-100%（極端に買い越し）'])
    return g.groupby(b, observed=True)[h].agg(回数='size', 平均='mean', 上がった率=lambda x: (x > 0).mean()).round(3)


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'extract':
        extract(sys.argv[2]); sys.exit()
    P = panel(); P.to_csv(OUT / 'panel.csv.gz', index=False)
    T = ic(P); Tr = ic(P, resid=True)
    parts = [f'サンプル {len(P):,} 週（5 通貨、{P.date.min():%Y}〜{P.date.max():%Y}）。IC = 順位の相関（+ なら指標が高いほどその通貨が上がる）。目安：|t| >= 2.5 かつ年・通貨で向きがそろう',
             '## 1. そのまま', T.to_string(index=False), '## 2. 直前 13 週の値動き（mom13）の分を除いたあと', Tr.to_string(index=False)]
    for f in ['am_idx', 'nc_idx', 'cm_idx', 'sm_idx', 'lev_idx']:
        for h in ('f8', 'f13'):
            parts += [f'## 3. {f} の極端さ → 次の {h[1:]} 週（週の値動きの大きさ単位、+ = その通貨が上）', extremes(P, f, h).to_string()]
    A = P.dropna(subset=['am_idx', 'f13']).copy(); A['期間'] = np.where(A.date < '2018-01-01', '2010-17', '2018-26')
    for per, g in A.groupby('期間'):
        parts += [f'## 4. am_idx の極端さ → 次の 13 週（{per}）', extremes(g, 'am_idx', 'f13').to_string()]
    for cur, g in A.groupby('cur'):
        parts += [f'## 5. am_idx の極端さ → 次の 13 週（{cur}）', extremes(g, 'am_idx', 'f13').to_string()]
    txt = '\n\n'.join(parts); (OUT / 'report.md').write_text(txt, encoding='utf-8'); print(txt)
