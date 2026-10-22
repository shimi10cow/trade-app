"""Master trade table: every core EA on every instrument (+ adopted variants), costs applied (FX 1.2 pip, gold 0.025%, BTC 0.08%).
Columns: ea, pair, tt (entry), et (exit), side, R, risk, entry, half (1 design / 2 check)."""
from pathlib import Path
import numpy as np, pandas as pd
RES = Path(__file__).parent / 'results'
DIRS = {'EURUSD': RES, 'USDJPY': RES / 'usdjpy', 'EURJPY': RES / 'eurjpy', 'GBPUSD': RES / 'gbpusd', 'XAUUSD': RES / 'xauusd', 'BTCUSD': RES / 'btcusd'}
COST = {'XAUUSD': 2.5, 'BTCUSD': 8.0}
SPLIT = {'BTCUSD': ((2017, 2021), (2022, 2026))}
CORE = [('R', 'regime2_R2c.csv'), ('T', 'regime2_T1t.csv'), ('L', 'tl_N2.csv'), ('A', 'retest_N1.csv'), ('C', 'step2/cl15_md4tri.csv'),
        ('J2', 'turn/jt2_h1major+hour0_10.csv'), ('J3', 'turn/j3_h41_s0_h1prot.csv'), ('EV', 'session/ev_18-21+0-3.csv'), ('P', 'pb/P4_maj0_rs0.5.csv')]
EXTRA = [('T2', 'EURUSD', 'regime2_T1t_axis.csv'), ('L2', 'XAUUSD', 'tl_N2_room1.csv'), ('S', 'XAUUSD', 'st2/S_ma_prov_buy_mt3_h1a1.csv'),
         ('S', 'BTCUSD', 'st2/S_ma_ma_buy_mt3_h1a2.csv')]
ADOPTED = {('R', 'EURUSD'), ('T', 'EURUSD'), ('L', 'EURUSD'), ('A', 'EURUSD'), ('C', 'EURUSD'), ('C', 'USDJPY'), ('J2', 'USDJPY'), ('L2', 'XAUUSD'), ('S', 'XAUUSD')}
def load1(ea, pair, f):
    p = DIRS[pair] / f
    if not p.exists(): return None
    d = pd.read_csv(p)
    if 'Rc' in d: x = pd.DataFrame(dict(R=d.Rc, tt=pd.to_datetime(d.time), et=pd.to_datetime(d.ExitTime)))
    else: x = pd.DataFrame(dict(R=d.R, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t)))
    x['side'] = d.side.values; x['risk'] = d.risk.values; x['entry'] = d.entry.values
    if pair in COST: x['R'] = x.R - (COST[pair] - 1.2) * 1e-4 / x.risk
    h1, h2 = SPLIT.get(pair, ((2005, 2015), (2016, 2026)))
    y = x.tt.dt.year; x = x[(y >= h1[0]) & (y <= h2[1]) & x.R.notna() & x.et.notna()].copy()
    x['half'] = np.where(x.tt.dt.year <= h1[1], 1, 2); x['ea'] = ea; x['pair'] = pair
    return x
def build():
    out = [load1(ea, p, f) for p in DIRS for ea, f in CORE] + [load1(*e) for e in EXTRA]
    T = pd.concat([o for o in out if o is not None], ignore_index=True)
    T['key'] = T.ea + '@' + T.pair; T['adopted'] = [(a, b) in ADOPTED for a, b in zip(T.ea, T.pair)]
    return T.sort_values('tt').reset_index(drop=True)
if __name__ == '__main__':
    import sys
    T = build(); T.to_pickle(sys.argv[1]); print(len(T), T.key.nunique())
