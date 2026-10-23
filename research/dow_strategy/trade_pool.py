"""All EA trades (key, pair, tt, side, R, half) across instruments, with the adopted set of the current candidate
(combo ④ + US30/US500 RSI(2)). Shared by the context studies (mtf_eval.py, ltf_pos.py)."""
import numpy as np, pandas as pd
import new_summary as N
S = N.S
ADOPT = {'R@EURUSD', 'T2@EURUSD', 'L@EURUSD', 'A@EURUSD', 'C@EURUSD', 'C@USDJPY', 'J2@USDJPY', 'L2@XAUUSD', 'S@XAUUSD',
         'Q@XAUUSD', 'Q@XAGUSD', 'T@US30', 'Q@US30', 'M@US30', 'M@US500'}
COLS = ['key', 'pair', 'tt', 'side', 'R', 'half']


def load_all():
    T = pd.read_pickle(f'{S}/feat/all_trades_xm.pkl')[COLS]
    Q = pd.read_pickle(f'{S}/feat/q_best.pkl'); Q = Q[Q.pair.isin(['XAUUSD', 'USDJPY'])].assign(key=lambda d: 'Q@' + d.pair, half=lambda d: np.where(d.tt.dt.year <= 2015, 1, 2))
    rows = [T, Q[COLS]]
    for sym in ('XAGUSD', 'US30', 'US500', 'JP225'):
        for ea, f in N.CORE:
            x = N.load(sym, f)
            if x is not None: rows.append(x.assign(key=f'{ea}@{sym}', pair=sym)[COLS])
    for sym, f in (('XAGUSD', 'q/Q_0.8_24_any_dow_ref_h4.csv'), ('US30', 'q/Q_1.0_24_ma_dow_ref_h1.csv')):
        x = N.load(sym, f)
        if x is not None: rows.append(x.assign(key=f'Q@{sym}', pair=sym)[COLS])
    for sym in ('US30', 'US500'):
        x = N.load(sym, 'rsi2/M_200_10_ma5_st.csv')
        if x is not None: rows.append(x.assign(key=f'M@{sym}', pair=sym)[COLS])
    X = pd.concat(rows, ignore_index=True); X['tt'] = pd.to_datetime(X.tt)
    X['adopt'] = X.key.isin(ADOPT)
    return X
