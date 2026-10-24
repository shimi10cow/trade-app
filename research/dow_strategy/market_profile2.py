"""Market character of an instrument from raw M5 (UTC): volatility, trading hours/weekends, hourly activity (JST),
trend persistence (variance ratio, autocorrelation of H1/H4/D1 returns), how often breakouts of the previous day's
range follow through, gaps. Compared side by side for EURUSD/USDJPY/XAUUSD/BTCUSD."""
import sys, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SRC = {'EURUSD': '/home/user/trade-app/research/datasets/raw/m5/EURUSD_M5.csv.gz',
       'USDJPY': '/home/user/trade-app/research/datasets/raw/m5/USDJPY_M5.csv.gz',
       'EURJPY': f'{S}/ws_EURJPY/research/datasets/raw/m5/EURJPY_M5.csv.gz', 'GBPUSD': f'{S}/ws_GBPUSD/research/datasets/raw/m5/GBPUSD_M5.csv.gz'}
for _s in ('XAUUSD', 'BTCUSD', 'GBPJPY', 'AUDJPY', 'CADJPY', 'CHFJPY', 'AUDUSD', 'USDCAD', 'USDCHF', 'XAGUSD', 'US30'):
    SRC[_s] = f'{S}/ws_{_s}/{_s}_M5_raw.csv.gz'
for _s in ('US500', 'JP225', 'OIL', 'NGAS'):
    SRC[_s] = f'{S}/ws_{_s}/{_s}_M15_raw.csv.gz'   # XM MT5 M15 (UTC), 2016/17-
if len(sys.argv) > 1: SRC = {k: v for k, v in SRC.items() if k in sys.argv[1:]}
rows = []
for sym, f in SRC.items():
    d = pd.read_csv(f, parse_dates=['time']).set_index('time').sort_index()
    d = d[d.index >= '2017-06-01']          # common period for a fair comparison
    lc = np.log(d.close)
    r = {}
    r['M5本数/年'] = len(d) / ((d.index[-1] - d.index[0]).days / 365.25)
    r['週末の足の割合'] = (d.index.dayofweek >= 5).mean()
    def rs(rule):
        x = d.resample(rule).agg(dict(open='first', high='max', low='min', close='last')).dropna(); return x
    D1 = rs('1D'); H1 = rs('1h'); H4 = rs('4h')
    r['日足の値幅中央(%)'] = ((D1.high - D1.low) / D1.close * 100).median()
    r['H1の値幅中央(%)'] = ((H1.high - H1.low) / H1.close * 100).median()
    for nm, x in (('H1', H1), ('H4', H4), ('D1', D1)):
        ret = np.log(x.close).diff().dropna()
        r[f'{nm}自己相関'] = ret.autocorr(1)
    # variance ratio: var of k-bar returns / (k * var of 1-bar) on H1 (>1 trending, <1 mean reverting)
    h1r = np.log(H1.close).diff().dropna()
    for k in (4, 24, 120):
        rk = np.log(H1.close).diff(k).dropna()
        r[f'分散比H1×{k}'] = rk.var() / (k * h1r.var())
    # previous-day breakout follow-through: day closes beyond yesterday's high/low after breaking it
    y = D1.shift(1)
    up = D1.high > y.high; dn = D1.low < y.low
    r['前日高値抜けで終値も上'] = ((D1.close > y.high) & up).sum() / up.sum()
    r['前日安値割れで終値も下'] = ((D1.close < y.low) & dn).sum() / dn.sum()
    # hourly activity in JST: share of mean absolute H1 move by JST hour
    act = (H1.high - H1.low) / H1.close
    jst = (H1.index + pd.Timedelta(hours=9)).hour
    a = act.groupby(jst).mean(); a = a / a.mean()
    r['活発な時間(JST)'] = ','.join(str(h) for h in a.sort_values(ascending=False).index[:4])
    r['静かな時間(JST)'] = ','.join(str(h) for h in a.sort_values().index[:4])
    # weekend vs weekday H1 range (BTC)
    wk = H1.index.dayofweek >= 5
    r['週末H1値幅/平日'] = (act[wk].mean() / act[~wk].mean()) if wk.any() else np.nan
    # trend share: fraction of days where |close-open| > 0.6 x range (directional days)
    r['方向の出た日の割合'] = ((D1.close - D1.open).abs() > 0.6 * (D1.high - D1.low)).mean()
    # big moves: share of days with range > 2x median (tail fatness)
    rng = (D1.high - D1.low) / D1.close
    r['大荒れ日(中央の2倍超)'] = (rng > 2 * rng.median()).mean()
    rows.append(pd.Series(r, name=sym)); print(sym, 'done', flush=True)
T = pd.DataFrame(rows).T
pd.set_option('display.width', 200); pd.set_option('display.max_colwidth', 40)
print(T.to_string(float_format=lambda v: f'{v:.3f}'))
T.to_csv(f'{S}/market_profile_all.csv' if len(sys.argv) == 1 else f'{S}/market_profile_' + '_'.join(sys.argv[1:]) + '.csv')
