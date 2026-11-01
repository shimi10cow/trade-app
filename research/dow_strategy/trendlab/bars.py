"""H1 bars for every instrument we have (broker prices), cached."""
import zipfile, sys, pandas as pd, numpy as np
R = '/home/user/trade-app/'
SRC = {'EURUSD': 'gz', 'USDJPY': 'gz', 'US500': 'mt5', 'JP225': 'mt5', 'OIL': 'mt5', 'NGAS': 'mt5',
       'XAUUSD': 'research/data/XAUUSD2003.M5.zip', 'AUDUSD': 'research/data/AUDUSD2003.M5.zip', 'AUDJPY': 'research/data/AUDJPY2003.M5.zip',
       'GBPUSD': 'GBPUSD2003.M5.zip', 'USDCAD': 'USDCAD2003.M5.zip', 'USDCHF': 'USDCHF2003.M5.zip', 'CADJPY': 'CADJPY2003.M5.zip',
       'CHFJPY': 'CHFJPY2003.M5.zip', 'EURJPY': 'EURJPY2003.M15.zip', 'XAGUSD': 'XAGUSD2003.M15.zip'}
def raw(sym):
    s = SRC[sym]
    if s == 'gz':
        d = pd.read_csv(R + f'{sym}_m1_M5.csv.gz', usecols=[0, 1, 2, 3, 4], parse_dates=['time'])
    elif s == 'mt5':
        d = pd.read_csv(R + f'{sym}Cash#_M15_MT5.csv', usecols=[0, 1, 2, 3, 4], encoding='utf-8-sig', parse_dates=['time']); d = d[d.time >= '2016-10-27 01:15']
    else:
        z = zipfile.ZipFile(R + s); d = pd.read_csv(z.open(z.namelist()[0]), dtype={'<TIME>': str})
        d = pd.DataFrame(dict(time=pd.to_datetime(d['<DTYYYYMMDD>'].astype(str) + d['<TIME>'].str.zfill(4), format='%Y%m%d%H%M'),
                              open=d['<OPEN>'], high=d['<HIGH>'], low=d['<LOW>'], close=d['<CLOSE>']))
    return d
for sym in (sys.argv[1:] or SRC):
    d = raw(sym).set_index('time')
    h = d.resample('1h', label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna().reset_index()
    h.columns = ['t', 'o', 'h', 'l', 'c']; h.to_pickle(f'/home/user/trendlab/h1_{sym}.pkl'); print(sym, len(h), h.t.iat[0].date(), h.t.iat[-1].date(), flush=True)
