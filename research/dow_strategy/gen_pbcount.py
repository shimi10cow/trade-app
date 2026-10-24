"""Pullback number for the viewer's mark tags (2026-10-21, v2: SMA20/75 cross is the main count).
For H1 and H4: after SMA20/SMA75 cross (and, for reference, after a Dow major turn), count how many times price made a
new high (sell: new low) after a confirmed swing low (sell: high) that formed after the start. Pullback number = count + 1.
A mark against the current SMA20/75 order is a 'break' entry (entered before the cross).
Writes <out>/pbc.json: {TF: [[avail_time, ma_side, n_ma, dow_side, n_dow], ...]} rows only where the state changes;
times = broker clock as epoch seconds (bar close).  Usage: python dow_strategy/gen_pbcount.py <out_dir>"""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load
from env_recognition import dow_trend
from env_recognition.ea_api import TF_LEN


class Pushes:
    """Counts 'confirmed counter swing -> new extreme' cycles since the side last changed."""
    def __init__(self):
        self.side, self.start, self.n, self.ext, self.armed = 0, 0, 0, None, False

    def step(self, i, side, hi, lo, conf):
        if side != self.side:
            self.side, self.start, self.n, self.armed = side, i, 0, False
            self.ext = hi if side == 1 else lo
        for e in conf:
            if e['idx'] > self.start and (e['kind'] == 'lo') == (self.side == 1):
                self.armed = True
        if self.side == 1 and hi > self.ext:
            self.ext = hi; self.n += self.armed; self.armed = False
        elif self.side == -1 and lo < self.ext:
            self.ext = lo; self.n += self.armed; self.armed = False
        return [int(self.side), int(self.n)]


if __name__ == '__main__':
    out = {}
    for tf in ('H1', 'H4'):
        df = load(tf, 'long').reset_index(drop=True)
        R = dow_trend.run(df, tf)
        dow = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['bars']]
        ma = np.sign(df.c.rolling(20).mean() - df.c.rolling(75).mean()).fillna(0).astype(int).to_numpy()
        conf = {}
        for e in R['pivot_events']:
            if e['action'] == 'confirm':
                conf.setdefault(e['available_idx'], []).append(e)
        ts = ((pd.to_datetime(df.t) + TF_LEN[tf] - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).tolist()
        h, l = df.h.to_numpy(float), df.l.to_numpy(float)
        A, B, rows = Pushes(), Pushes(), []
        for i in range(len(df)):
            c = conf.get(i, [])
            st = A.step(i, ma[i], h[i], l[i], c) + B.step(i, dow[i], h[i], l[i], c)
            if not rows or rows[-1][1:] != st:
                rows.append([ts[i]] + st)
        out[tf] = rows
        print(tf, len(df), 'bars', len(rows), 'rows', flush=True)
    Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)
    json.dump(out, open(Path(sys.argv[1]) / 'pbc.json', 'w'), separators=(',', ':'))
