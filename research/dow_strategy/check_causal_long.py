"""Look-ahead check on the long data (user request 2026-10-19).

For sampled trade times ts (signal-bar close), recompute everything from data CUT at ts
(only bars whose close <= ts) and compare with what the full-history run reported for that time:
  - H4 / H1 / D1 major trend and protected level (押し安値/戻り高値), provisional trend
  - H4 / H1 trend stage, H4 live lines + broken flags
  - M15 Dow pivots used by the trailing stop (every pivot known by ts must be identical)
Also checks over the full H4 / H1 history that the protected level only changes on a Dow event
of that bar, and that an up trend never ends a bar with close below its protected low (and vice versa).
Usage: python dow_strategy/check_causal_long.py [n_samples]
"""
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import EnvRecognizer, TF_LEN  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
from env_recognition.pivots import pivot_events  # noqa: E402
from long_features import stage_arrays  # noqa: E402

OUT = Path(__file__).with_name('results')
import os
CONTROL = os.environ.get('CAUSAL_CONTROL') == '1'
F = {tf: load(tf, 'long').reset_index(drop=True) for tf in ('D1', 'H4', 'H1', 'M15')}


def cut(tf, ts):
    df = F[tf]
    return df[pd.to_datetime(df.t) + TF_LEN[tf] <= ts].reset_index(drop=True)


def snapshot(frames_cut_or_full, ts):
    """State known at ts. With full frames the recognizer picks the last closed bar itself."""
    env = EnvRecognizer({tf: frames_cut_or_full[tf] for tf in ('D1', 'H4')})
    s = env.state_at(ts)
    out = {}
    for tf in ('D1', 'H4'):
        k = env.last_closed(tf, ts)
        x = s[tf]
        out[tf] = dict(trend=x['trend'], prot=x['protected'], ptrend=x['prov_trend'], pprot=x['prov_protected'],
                       lines=sorted((l['key'], round(l['value'], 6), l['broken']) for l in x['lines']))
        if tf == 'H4':
            out['H4']['stage'] = int(stage_arrays(env.tf['H4']['res'], k + 1)[k])
    h1 = frames_cut_or_full['H1']
    k1 = int((pd.to_datetime(h1.t) + TF_LEN['H1'] <= ts).sum()) - 1
    r = dow_trend.run(h1, 'H1')
    out['H1'] = dict(trend=r['bars'][k1][0], prot=r['bars'][k1][1], stage=int(stage_arrays(r, k1 + 1)[k1]))
    return out


def check_one(ts):
    ts = pd.Timestamp(ts)
    win = pd.Timedelta(days=400)          # keep a long warm-up but bound the work
    lo = ts - win
    part = {tf: F[tf][(pd.to_datetime(F[tf].t) >= lo - pd.Timedelta(days=2000))].reset_index(drop=True)
            for tf in ('D1', 'H4', 'H1')}
    # "full" = same start, data running 60 days PAST ts (the future is present); "cut" = data ends at ts
    full = {tf: d[pd.to_datetime(d.t) < ts + pd.Timedelta(days=60)].reset_index(drop=True) for tf, d in part.items()}
    leak = pd.Timedelta(days=1) if CONTROL else pd.Timedelta(0)   # control: deliberately leak 1 day of future
    cutd = {tf: d[pd.to_datetime(d.t) + TF_LEN[tf] <= ts + leak].reset_index(drop=True) for tf, d in part.items()}
    a, b = snapshot(full, ts), snapshot(cutd, ts + leak)
    diffs = [f'{tf}.{k}: future={a[tf][k]} cut={b[tf][k]}' for tf in a for k in a[tf] if a[tf][k] != b[tf][k]]
    # M15 trailing pivots: pivots known by ts must match exactly
    m = F['M15']; mt = pd.to_datetime(m.t)
    i0 = int((mt < lo).sum())
    seg_full = m.iloc[i0:int((mt < ts + pd.Timedelta(days=10)).sum())].reset_index(drop=True)
    seg_cut = m.iloc[i0:int((mt + TF_LEN['M15'] <= ts).sum())].reset_index(drop=True)
    kmax = len(seg_cut) - 1
    pf = [(e['action'], e['kind'], e['idx'], e['price'], e['available_idx']) for e in pivot_events(seg_full) if e['available_idx'] <= kmax]
    pc = [(e['action'], e['kind'], e['idx'], e['price'], e['available_idx']) for e in pivot_events(seg_cut)]
    if pf != pc:
        diffs.append(f'M15 pivots differ ({len(pf)} vs {len(pc)})')
    return str(ts), diffs


def invariants(tf):
    df = F[tf]
    r = dow_trend.run(df, tf)
    c = df.c.to_numpy(float)
    ev_bars = {e['idx'] for e in r['events'] if e.get('machine') == 'major'}
    bad_close, bad_move, moves = 0, 0, 0
    for k in range(1, len(df)):
        tr, pr = r['bars'][k]
        if tr == 'up' and pr is not None and c[k] < pr - 1e-9: bad_close += 1
        if tr == 'down' and pr is not None and c[k] > pr + 1e-9: bad_close += 1
        if pr != r['bars'][k - 1][1]:
            moves += 1
            if k not in ev_bars: bad_move += 1
    return tf, dict(bars=len(df), protected_moves=moves, moves_without_event=bad_move, close_beyond_protected=bad_close)


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    tr = pd.read_csv(OUT / 'long_trades_1.csv', parse_dates=['time'])
    tr = tr[tr.time >= '2005-01-01'].reset_index(drop=True)   # needs warm-up history
    rng = np.random.default_rng(0)
    times = sorted(tr.time.iloc[rng.choice(len(tr), n, replace=False)] + pd.Timedelta(minutes=15))
    with Pool(4) as pool:
        inv = pool.map(invariants, ['H4', 'H1', 'D1'])
        res = pool.map(check_one, times)
    for tf, d in inv:
        print('invariant', tf, d, flush=True)
    bad = [(t, d) for t, d in res if d]
    print(f'look-ahead check: {len(res)} sample times, {len(bad)} with differences')
    for t, d in bad:
        print(' ', t, *d, sep='\n    ')
