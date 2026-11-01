"""Run the adopted live EAs of one symbol over its whole history (one Frames), save every closed trade."""
import sys, time, zipfile
sys.path.insert(0, '/home/user/trade-app')
import numpy as np, pandas as pd
from mt5_ea.live.core import Frames, to_space
from mt5_ea.live.registry import ADOPTED
R = '/home/user/trade-app/'
def load(sym):
    if sym in ('US500', 'JP225'):
        d = pd.read_csv(R + f'{sym}Cash#_M15_MT5.csv', usecols=[0, 1, 2, 3, 4], encoding='utf-8-sig', parse_dates=['time'])
        d = d[d.time >= '2016-10-27 01:15'].reset_index(drop=True); start = '2017-12-01'
    elif sym == 'XAUUSD':
        z = zipfile.ZipFile(R + 'research/data/XAUUSD2003.M5.zip'); d = pd.read_csv(z.open(z.namelist()[0]), dtype={'<TIME>': str})
        d = pd.DataFrame(dict(time=pd.to_datetime(d['<DTYYYYMMDD>'].astype(str) + d['<TIME>'].str.zfill(4), format='%Y%m%d%H%M'), open=d['<OPEN>'], high=d['<HIGH>'], low=d['<LOW>'], close=d['<CLOSE>']))
        d = d.set_index('time').resample('15min', label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna().reset_index(); start = '2005-01-01'
    else:
        d = pd.read_csv(R + f'{sym}_m1_M5.csv.gz', usecols=[0, 1, 2, 3, 4], parse_dates=['time'])
        d = d.set_index('time').resample('15min', label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna().reset_index(); start = '2005-01-01'
    return pd.DataFrame(dict(t=d.time, o=to_space(sym, d.open), h=to_space(sym, d.high), l=to_space(sym, d.low), c=to_space(sym, d.close))), start
sym = sys.argv[1]; t0 = time.time(); m, start = load(sym); F = Frames(m, start); print(sym, 'frames', f'{time.time() - t0:.0f}s', flush=True)
m.to_pickle(f'/home/user/trend_diag/m15_{sym}.pkl')
for ea in [e for e in ADOPTED if e.symbol == sym]:
    t1 = time.time()
    try:
        tr = ea.run(F, None)['trades']
        tr = pd.DataFrame(tr).copy(); tr['ea'] = ea.key; tr.to_pickle(f'/home/user/trend_diag/tr_{ea.key.replace("@", "_")}.pkl')
        print(ea.key, len(tr), 'trades', list(tr.columns)[:14], f'{time.time() - t1:.0f}s', flush=True)
    except Exception as ex:
        import traceback; traceback.print_exc(); print(ea.key, 'FAILED', ex, flush=True)
