"""User review follow-up (2026-10-19): existing EA + (1) skip when an opposing H4 wall is close,
(2) stop behind structure instead of M15 SMA200 +/- 10 pips.

Walls (buy; mirror for sell), all known at the signal-bar close:
  active H4 zones above entry (bottom edge), the latest confirmed H4 swing high above entry,
  the H4 protected high when the H4 trend is down.   skip if  distance to nearest wall < k x risk
Stops:
  base      M15 SMA200 -/+ 10 pips (current EA)
  M15swing  1 pip beyond the latest confirmed M15 Dow swing low/high on the far side of entry
  H1swing   1 pip beyond the latest confirmed H1 Dow swing low/high on the far side of entry
  H1prot    1 pip beyond the H1 Dow protected level when the H1 trend agrees, else H1swing
  wider     the wider of base and M15swing
Min stop 10 pips everywhere. Develop 2020-24, check 2025-26, reference 2015-19. Cost 1.2 pip.
Also scores each stop rule against the user's ideal stops (dow_strategy/feedback/*.json).
Usage: EA_M15_CACHE=<broker-time csv> python dow_strategy/wall_and_stop.py
"""
import bisect
import glob
import json
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'core'))
import engine_m15 as E  # noqa: E402
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import EnvRecognizer, TF_LEN  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
from env_recognition.pivots import pivot_events  # noqa: E402

PIP, COST = 1e-4, 1.2e-4
HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
M15 = 15 * 60


def pivot_index(df, tf, events):
    """Pivot confirm/relocate events sorted by the close time at which they became known."""
    t = pd.to_datetime(df.t)
    rows = sorted(((t[e['available_idx']] + TF_LEN[tf], e['id'], e['kind'], e['price']) for e in events), key=lambda x: x[0])
    return [r[0] for r in rows], rows


def latest_beyond(idx, ts, kind, entry, side, look=60):
    """Most recent confirmed swing of `kind` known by ts that lies beyond entry on the stop side."""
    keys, rows = idx
    j = bisect.bisect_right(keys, ts) - 1
    seen = set()
    while j >= 0 and look > 0:
        _, pid, k, price = rows[j]
        j -= 1
        if k != kind or pid in seen:
            continue
        seen.add(pid); look -= 1
        if (price < entry) if side == 1 else (price > entry):
            return price
    return None


print('prep...', flush=True)
m15 = load('M15', 'long')
P15 = pivot_index(m15, 'M15', pivot_events(m15))
h1 = load('H1', 'long').reset_index(drop=True)
H1R = dow_trend.run(h1, 'H1')
P1 = pivot_index(h1, 'H1', H1R['pivot_events'])
H1C = list(pd.to_datetime(h1.t) + TF_LEN['H1'])
ENV = EnvRecognizer({'H4': load('H4', 'long')})
H4R = ENV.tf['H4']['res']
P4 = pivot_index(ENV.tf['H4']['df'], 'H4', H4R['pivot_events'])
print('prep done', flush=True)


def stop_price(mode, t, side, entry, base):
    ts = t + pd.Timedelta(minutes=15)
    kind = 'lo' if side == 1 else 'hi'
    if mode == 'base':
        return base
    if mode in ('M15swing', 'wider'):
        p = latest_beyond(P15, ts, kind, entry, side)
        s = None if p is None else p - side * PIP
        if mode == 'wider':
            return base if s is None else (min(s, base) if side == 1 else max(s, base))
        return s if s is not None else base
    k = bisect.bisect_right(H1C, ts) - 1
    if mode == 'H1prot' and k >= 0:
        tr, prot = H1R['bars'][k]
        if tr == ('up' if side == 1 else 'down') and prot is not None and ((prot < entry) if side == 1 else (prot > entry)):
            return prot - side * PIP
    p = latest_beyond(P1, ts, kind, entry, side)
    return base if p is None else p - side * PIP


def wall_dist(t, side, entry):
    ts = t + pd.Timedelta(minutes=15)
    s = ENV.state_at(ts)['H4']
    if s is None:
        return None
    lv = [z['bottom'] if side == 1 else z['top'] for z in s['zones']]
    p = latest_beyond(P4, ts, 'hi' if side == 1 else 'lo', entry, -side)
    if p is not None:
        lv.append(p)
    if s['trend'] == ('down' if side == 1 else 'up') and s['protected'] is not None:
        lv.append(s['protected'])
    d = [side * (x - entry) for x in lv if side * (x - entry) > 0]
    return min(d) if d else None


def make_cfg(stop='base', wall=None):
    kw = {}
    if stop != 'base' or wall is not None:
        def sl_fn(t, side, entry, base):
            sl = stop_price(stop, t, side, entry, base)
            sl = min(sl, entry - 10 * PIP) if side == 1 else max(sl, entry + 10 * PIP)
            if wall is not None:
                d = wall_dist(t, side, entry)
                if d is not None and d < wall * abs(entry - sl):
                    return None
            return sl
        kw['sl_fn'] = sl_fn
    return E.Config(**kw)


def stats(r):
    if not len(r):
        return dict(n=0)
    w = r > 0
    eq = np.cumsum(r)
    return dict(n=len(r), sumR=round(r.sum(), 1), PF=round(r[w].sum() / max(1e-9, -r[~w].sum()), 2),
                maxDD=round((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(), 1), win=round(w.mean(), 2))


def run(job):
    name, stop, wall = job
    tr = E.run_pair('EURUSD', make_cfg(stop, wall))
    tr['Rc'] = tr.R - COST / tr.risk
    y = pd.to_datetime(tr.time).dt.year
    out = {'risk_pips_med': round(float(tr.risk.median() / PIP), 1)}
    for lab, a, b in (('開発2020-24', 2020, 2024), ('確認2025-26', 2025, 2026), ('参考2015-19', 2015, 2019)):
        out[lab] = stats(tr.Rc[(y >= a) & (y <= b)].to_numpy())
    tr.to_csv(OUT / f'wall_stop_trades_{name}.csv', index=False)
    return name, out


def ideal_match():
    """How close each stop rule is to the stops the user drew (pips, entry = EA entry)."""
    rows = []
    for f in glob.glob(str(HERE / 'feedback' / '*.json')):
        x = json.load(open(f))
        I = x.get('ideal') or {}
        if 'sl' not in I:
            continue
        # stop measured from the user's ideal entry when one was drawn, else from the EA entry
        own = 'entry' in I
        t = pd.Timestamp(I['entry']['t'] if own else x['t'], unit='s')
        en = I['entry']['p'] if own else x['entry_px']
        r = dict(t=t, entry='理想' if own else 'EA', ideal=round(abs(en - I['sl']['p']) / PIP, 1))
        for m in ('base', 'M15swing', 'H1swing', 'H1prot', 'wider'):
            if own and m in ('base', 'wider'):
                r[m] = np.nan; continue
            r[m] = round(abs(en - stop_price(m, t, x['side'], en, x['sl_px'])) / PIP, 1)
        rows.append(r)
    return pd.DataFrame(rows)


JOBS = [('base', 'base', None), ('M15swing', 'M15swing', None), ('H1swing', 'H1swing', None), ('H1prot', 'H1prot', None),
        ('wider', 'wider', None), ('wall0.5', 'base', 0.5), ('wall1', 'base', 1.0), ('wall1.5', 'base', 1.5), ('wall2', 'base', 2.0)]

if __name__ == '__main__':
    jobs = [j for j in JOBS if not sys.argv[1:] or j[0] in sys.argv[1:]]
    rows = {}
    with Pool(4) as pool:
        for name, out in pool.imap(run, jobs):
            rows[name] = out
            d, c, p = out['開発2020-24'], out['確認2025-26'], out['参考2015-19']
            f = lambda s: f"n={s['n']} {s.get('sumR', 0):+.1f}R PF{s.get('PF', 0)} DD{s.get('maxDD', 0)}"
            print(f"{name:9s} SL中央値{out['risk_pips_med']}pips | 開発 {f(d)} | 確認 {f(c)} | 参考 {f(p)}", flush=True)
    flat = {k: {f'{p}_{m}': v[p].get(m) for p in ('開発2020-24', '確認2025-26', '参考2015-19') for m in ('n', 'sumR', 'PF', 'maxDD', 'win')}
            | {'risk_pips_med': v['risk_pips_med']} for k, v in rows.items()}
    pd.DataFrame(flat).T.to_csv(OUT / 'wall_stop_summary.csv')
    M = ideal_match()
    print('\nあなたが引いた理想の損切り（pips）とルールの損切り幅', flush=True)
    print(M.to_string(index=False))
    for m in ('base', 'M15swing', 'H1swing', 'H1prot', 'wider'):
        print(f'  {m:9s} 理想との差の中央値 {np.nanmedian(abs(M[m] - M.ideal)):.1f}pips（{M[m].notna().sum()}件）', flush=True)
