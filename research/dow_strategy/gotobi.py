"""Gotobi days (五十日, user 2026-10-23): on the 5th / 10th / 15th / 20th / 25th and the month end (moved to the previous
Japanese business day when it falls on a weekend or a Japanese holiday) importers buy dollars at the Tokyo fix (9:55 JST),
so USDJPY is said to rise into the fix and fall back after it. Broker time = Europe/Athens, converted to JST.
For every Japanese business day: move (in pips of the pair, and in units of the day's ATR(H1, 24 x median)) over
  pre  : 08:00 -> 10:00 JST (into the fix)
  post : 10:00 -> 15:00 JST (after the fix)
  rest : 15:00 -> next 08:00
gotobi vs other days, by half (2005-15 / 2016-26), for USDJPY and the yen crosses; then simple trades with XM-like cost:
buy 8:00 -> sell 10:00 on gotobi; sell 10:00 -> buy back 15:00 on gotobi."""
import datetime as dt
import numpy as np, pandas as pd, jpholiday
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
PAIRS = {'USDJPY': 1.0, 'EURJPY': 1.6, 'GBPJPY': 3.3, 'AUDJPY': 1.5, 'CADJPY': 2.5, 'CHFJPY': 1.5}   # cost in pips (round trip)


def biz(d): return d.weekday() < 5 and not jpholiday.is_holiday(d)


def gotobi_days(y0=2003, y1=2026):
    out = set()
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
            for dd in (5, 10, 15, 20, 25, last):
                d = dt.date(y, m, dd)
                while not biz(d): d -= dt.timedelta(days=1)
                out.add(d)
    return out


G = gotobi_days()
rows = []
for sym, cost in PAIRS.items():
    m = pd.read_csv(f'{S}/ws_{sym}/M15_broker.csv', parse_dates=['time'])
    v = m.close.median()
    px = m[['open', 'close']].copy()
    if v > 50: px = np.log(px)              # raw quotes
    elif v < 3: px = np.log(px * 100)       # /100 workspaces
    t = pd.DatetimeIndex(m.time).tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').tz_convert('Asia/Tokyo').tz_localize(None)
    s = pd.Series(px.open.to_numpy(), index=t); s = s[s.index.notna()]; s = s[~s.index.duplicated()]
    lvl = float(np.exp(np.log(m.close.median() * (100 if v < 3 else 1)))) if v < 50 and v >= 3 else (m.close.median() * (100 if v < 3 else 1))
    if 3 <= v <= 50: lvl = float(np.exp(v))
    pip = 0.01 / lvl                         # one pip in log units
    days = pd.Series(s.index.normalize().unique())
    for d in days:
        dd = d.date()
        if not biz(dd): continue
        def at(h):
            k = s.index.searchsorted(d + pd.Timedelta(hours=h))
            return s.iloc[k] if k < len(s) and s.index[k] - (d + pd.Timedelta(hours=h)) < pd.Timedelta('30min') else np.nan
        p8, p10, p15, n8 = at(8), at(10), at(15), at(32)
        rows.append(dict(sym=sym, d=d, gotobi=dd in G, pre=(p10 - p8) / pip, post=(p15 - p10) / pip, rest=(n8 - p15) / pip, cost=cost,
                         half=1 if dd.year <= 2015 else 2, wd=dd.weekday()))
D = pd.DataFrame(rows).dropna(); D = D[D.d.dt.year >= 2005]; D.to_pickle(f'{S}/feat/gotobi.pkl')
pd.set_option('display.width', 220)


def t(x): return x.mean() / (x.std() / np.sqrt(len(x))) if len(x) > 2 else np.nan


print('== 平均の動き（pips）と t 値：五十日 vs それ以外')
g = D.groupby(['sym', 'half', 'gotobi']).agg(n=('pre', 'size'), pre=('pre', 'mean'), pre_t=('pre', t), post=('post', 'mean'), post_t=('post', t),
                                               pre_up=('pre', lambda x: (x > 0).mean()))
print(g.round(2).to_string())
print('\n== 簡単な売買（五十日だけ、コスト込み pips／回、合計 pips、勝率）')
for sym, x in D[D.gotobi].groupby('sym'):
    for h, y in x.groupby('half'):
        a = y.pre - y.cost; b = -y.post - y.cost
        print(f'{sym} {"前半" if h == 1 else "後半"} n={len(y)}  8時買い→10時売り {a.mean():+.2f} pips 合計{a.sum():+.0f} 勝率{(a > 0).mean():.0%}'
              f'  |  10時売り→15時買い戻し {b.mean():+.2f} pips 合計{b.sum():+.0f} 勝率{(b > 0).mean():.0%}')
print('\n== ドル円：五十日の種類別（8→10 時の平均 pips、前半/後半）')
u = D[(D.sym == 'USDJPY') & D.gotobi].copy(); u['kind'] = np.where(u.d.dt.day >= 28, '月末', np.where(u.wd == 4, '金曜の五十日', '平日'))
print(u.groupby(['kind', 'half']).pre.agg(['size', 'mean']).unstack('half').round(2).to_string())
print('\n== ドル円：年ごとの 8→10 時の平均 pips（五十日 − それ以外）')
w = D[D.sym == 'USDJPY'].assign(y=lambda d: d.d.dt.year).groupby(['y', 'gotobi']).pre.mean().unstack(); print((w[True] - w[False]).round(2).to_string())
