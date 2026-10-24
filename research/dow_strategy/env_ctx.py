"""Causal H4 context used as environment filters (2026-10-20):
  sd = distance beyond the daily SMA200 (H4 SMA1200) on the trade side (ATR units)  -> sd>0 = with the daily side
  er = H4 efficiency ratio over 200 bars (low = back-and-forth, high = one-way)
  sh = distance beyond the H4 SMA200 on the trade side (ATR units)
All values use only H4 bars closed at time t."""
import bisect, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load
from env_recognition.ea_api import TF_LEN
from env_recognition.pivots import atr
_h4 = load('H4', 'long').reset_index(drop=True)
_c = pd.Series(_h4.c.to_numpy(float)); _A = atr(_h4); _C4 = list(pd.to_datetime(_h4.t) + TF_LEN['H4'])
_S1200 = _c.rolling(1200).mean().to_numpy(); _S200 = _c.rolling(200).mean().to_numpy()
_ER = (_c.diff(200).abs() / _c.diff().abs().rolling(200).sum()).to_numpy(); _cv = _c.to_numpy()
_S75 = _c.rolling(75).mean().to_numpy()
try:   # causal range score from range_detect.py (high = range-like, fitted to the user's H4 state labels)
    import numpy as _np
    _RS = _np.load(Path(__file__).with_name('results') / 'h4_range_score.npy')
except FileNotFoundError:
    _RS = None
# automatic triangles (triangles.py v2): active from the bar that made it known until the breakout bar closed
_TRI = {}
try:
    _ti = pd.read_csv(Path(__file__).with_name('results') / 'tri_intervals.csv', parse_dates=['known', 'end'])
    for _tf, _g in _ti.groupby('tf'):
        _TRI[_tf] = _g.sort_values('known')
except FileNotFoundError:
    pass


def tri_active(t, tf='H4', wmax=10.0):
    g = _TRI.get(tf)
    if g is None:
        return False
    g = g[(g.known <= t) & (g.end > t) & (g.w0 <= wmax)]
    return len(g) > 0


def ctx_at(t, s):
    k = bisect.bisect_right(_C4, t) - 1
    return dict(sd=s * (_cv[k] - _S1200[k]) / _A[k], er=_ER[k], sh=s * (_cv[k] - _S200[k]) / _A[k], d75=s * (_cv[k] - _S75[k]) / _A[k], rs=(_RS[k] if _RS is not None else float('nan')))


def env_ok(cfg, t, s):
    """cfg keys: dside (sd > value), env 'T' (sd>0 & er>0.1) / 'R' (er<0.08 & sh<3),
    maxdev (|distance from H4 SMA75| <= value ATR), notri ('H4'/'H1': no entry while an automatic triangle is forming)."""
    if cfg.get('dside') is None and not cfg.get('env') and cfg.get('maxdev') is None and not cfg.get('notri'):
        return True
    x = ctx_at(t, s)
    if cfg.get('dside') is not None and not x['sd'] > cfg['dside']:
        return False
    if cfg.get('env') == 'T' and not (x['sd'] > 0 and x['er'] > 0.1):
        return False
    if cfg.get('env') == 'R' and not (x['er'] < 0.08 and x['sh'] < 3):
        return False
    if cfg.get('env') == 'R2' and not (x['rs'] > cfg.get('rs_hi', 0.6) and x['sh'] < 3):
        return False
    if cfg.get('env') == 'T2' and not (x['rs'] < cfg.get('rs_lo', 0.4) and x['sd'] > 0):
        return False
    if cfg.get('maxdev') is not None and abs(x['d75']) > cfg['maxdev']:
        return False
    if cfg.get('notri') and tri_active(t, cfg['notri']):
        return False
    return True
