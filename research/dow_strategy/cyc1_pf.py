import sys
import pandas as pd
from pfx import ev, BASE9, BASE9T2
T = pd.read_pickle(sys.argv[1])
ev(T, BASE9, label='9本（現行）'); ev(T, BASE9T2, label='9本 T→T2')
Pp = T[(T.ea == 'P') & (T.ns > 0)].copy(); Pp['key'] = 'P+@' + Pp.pair
for p in ('XAUUSD', 'USDJPY', 'BTCUSD'):
    ev(T, BASE9T2, Pp[Pp.pair == p], f'+P+ {p}'); ev(T, BASE9T2, T[T.key == f'P@{p}'], f'+P {p}')
ev(T, BASE9T2, Pp[Pp.pair.isin(['XAUUSD', 'USDJPY'])], '+P+ 金・円')
ev(T, BASE9T2, T[T.key.isin(['P@XAUUSD', 'P@USDJPY'])], '+P 金・円')
