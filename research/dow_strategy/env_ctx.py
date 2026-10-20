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


def ctx_at(t, s):
    k = bisect.bisect_right(_C4, t) - 1
    return dict(sd=s * (_cv[k] - _S1200[k]) / _A[k], er=_ER[k], sh=s * (_cv[k] - _S200[k]) / _A[k])


def env_ok(cfg, t, s):
    """cfg keys: dside (sd > value), env 'T' (sd>0 & er>0.1) / 'R' (er<0.08 & sh<3)."""
    if cfg.get('dside') is None and not cfg.get('env'):
        return True
    x = ctx_at(t, s)
    if cfg.get('dside') is not None and not x['sd'] > cfg['dside']:
        return False
    if cfg.get('env') == 'T' and not (x['sd'] > 0 and x['er'] > 0.1):
        return False
    if cfg.get('env') == 'R' and not (x['er'] < 0.08 and x['sh'] < 3):
        return False
    return True
