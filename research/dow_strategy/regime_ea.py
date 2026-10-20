"""Environment-gated versions of the existing EA, run inside the engine (2026-10-20).
  EA-R : existing EA (long MA)              + gate: H4 ER200 < er_max and price < side_max ATR beyond H4 SMA200 (trade side)
  EA-T : existing EA w/o long MA + H1 Dow   + gate: price on the trade side of the daily SMA200 (H4 SMA1200) by > side_min ATR
                                                    and H4 ER200 > er_min
All features use only H4 bars closed at the signal time. Usage: EA_M15_CACHE=<csv> python dow_strategy/regime_ea.py [names]"""
import bisect, sys, time
from multiprocessing import Pool
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import long_validation as LV  # noqa: E402  (engine, h1_ok, stats)
from env_recognition.data import load
from env_recognition.ea_api import TF_LEN
from env_recognition.pivots import atr

h4 = load('H4', 'long').reset_index(drop=True)
c4 = pd.Series(h4.c.to_numpy(float)); A4 = atr(h4)
C4 = list(pd.to_datetime(h4.t) + TF_LEN['H4'])
SMA200 = c4.rolling(200).mean().to_numpy(); SMA1200 = c4.rolling(1200).mean().to_numpy()
ER200 = (c4.diff(200).abs() / c4.diff().abs().rolling(200).sum()).to_numpy()


def feat(t, s):
    k = bisect.bisect_right(C4, t) - 1
    return dict(er=ER200[k], side_h=s * (c4[k] - SMA200[k]) / A4[k], side_d=s * (c4[k] - SMA1200[k]) / A4[k])


def gate_R(er_max, side_max):
    def f(t, s):
        x = feat(t, s); return x['er'] < er_max and x['side_h'] < side_max
    return f


def gate_T(side_min, er_min):
    def f(t, s):
        x = feat(t, s); return LV.h1_ok(t, s) and x['side_d'] > side_min and x['er'] > er_min
    return f


PT = LV.trail.sort_values('confirm_time').reset_index(drop=True)
PTT = list(PT.confirm_time)


def swing_sl(pips):
    def f(t, s, entry, sl):
        j = bisect.bisect_right(PTT, t) - 1
        want = 'L' if s == 1 else 'H'
        while j >= 0 and PT.kind[j] != want:
            j -= 1
        if j < 0:
            return sl
        p = PT.price[j] - s * pips * 1e-4
        return p if s * (entry - p) > 0 else None
    return f


SPECS = {
    'R3': ('EA-R ER<0.08 side_h<3 P3まで', lambda: LV.E.Config(extra_filter=gate_R(0.08, 3), max_entry_point=3)),
    'T3': ('EA-T side_d>0 ER>0.10 P3まで', lambda: LV.E.Config(use_long_ma=False, extra_filter=gate_T(0, 0.10), max_entry_point=3)),
    'R4': ('EA-R ER<0.08 side_h<3 M15スイング+15p損切り', lambda: LV.E.Config(extra_filter=gate_R(0.08, 3), sl_fn=swing_sl(15))),
    'T4': ('EA-T side_d>0 ER>0.10 M15スイング+15p損切り', lambda: LV.E.Config(use_long_ma=False, extra_filter=gate_T(0, 0.10), sl_fn=swing_sl(15))),
    'R1': ('EA-R ER<0.08 side_h<3', lambda: LV.E.Config(extra_filter=gate_R(0.08, 3))),
    'R2': ('EA-R ER<0.10 side_h<3', lambda: LV.E.Config(extra_filter=gate_R(0.10, 3))),
    'T1': ('EA-T side_d>0 ER>0.10', lambda: LV.E.Config(use_long_ma=False, extra_filter=gate_T(0, 0.10))),
    'T2': ('EA-T side_d>0 ER>0.08', lambda: LV.E.Config(use_long_ma=False, extra_filter=gate_T(0, 0.08))),
}


def run2(key):
    name, mk = SPECS[key]; t0 = time.time()
    tr = LV.E.run_pair('EURUSD', mk()); tr['Rc'] = tr.R - LV.COST / tr.risk
    tr.to_csv(LV.OUT / f'regime_{key}.csv', index=False)
    return key, name, tr, time.time() - t0


if __name__ == '__main__':
    keys = sys.argv[1:] or list(SPECS)
    with Pool(min(4, len(keys))) as pool:
        for key, name, tr, sec in pool.imap_unordered(run2, keys):
            y = pd.to_datetime(tr.time).dt.year; r = tr.Rc
            b = [r[(y >= a) & (y <= z)].sum() for a, z in ((2003, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]
            yy = tr.groupby(y).Rc.sum()
            print(f"[{key}] {name} ({sec:.0f}s) {LV.stats(r.to_numpy())} 負け年{(yy < 0).sum()}/{len(yy)} | " + ' '.join(f'{v:+.1f}' for v in b), flush=True)
