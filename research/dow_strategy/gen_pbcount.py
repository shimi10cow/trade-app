"""Pullback number per Dow trend, for the viewer's mark tags (2026-10-21).
For H1 and H4: after each major turn, count swing lows (up trend) / highs (down trend) that formed AFTER the turn and
were confirmed. Buy pullback number = confirmed lows + 1. Writes <out>/pbc.json:
  {TF: [[avail_time, trend(1/-1/0), n_lo, n_hi], ...]}  rows only where the state changes; times = broker clock as epoch.
Usage: python dow_strategy/gen_pbcount.py <out_dir>"""
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load
from env_recognition import dow_trend
from env_recognition.ea_api import TF_LEN

out = {}
for tf in ('H1', 'H4'):
    df = load(tf, 'long').reset_index(drop=True)
    R = dow_trend.run(df, tf)
    tr = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['bars']]
    conf = {}
    for e in R['pivot_events']:
        if e['action'] == 'confirm':
            conf.setdefault(e['available_idx'], []).append(e)
    ts = ((pd.to_datetime(df.t) + TF_LEN[tf] - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).tolist()
    rows, cur, turn_i, nlo, nhi, seen = [], 0, 0, 0, 0, set()
    for i in range(len(df)):
        if tr[i] != cur:
            cur, turn_i, nlo, nhi = tr[i], i, 0, 0
        for e in conf.get(i, []):
            if e['id'] in seen or e['idx'] <= turn_i:
                continue
            seen.add(e['id'])
            if e['kind'] == 'lo': nlo += 1
            else: nhi += 1
        st = [cur, nlo, nhi]
        if not rows or rows[-1][1:] != st:
            rows.append([ts[i]] + st)
    out[tf] = rows
    print(tf, len(df), 'bars', len(rows), 'rows', flush=True)
Path(sys.argv[1]).mkdir(parents=True, exist_ok=True)
json.dump(out, open(Path(sys.argv[1]) / 'pbc.json', 'w'), separators=(',', ':'))
