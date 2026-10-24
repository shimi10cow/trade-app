"""Parity tests for the ported EAs (2026-10-24).

Test 1 (same trades): run the ported EA on the research workspace's own data and start date, entry-bar check OFF exactly
        like the research files, and compare trade by trade with the research result file.
Test 2 (no future data): cut the data at several points; trades entered before each cut must come out the same as in the
        full run (entry time, side, entry, initial stop), and a trade still open at the cut must be open in the full run too.
Usage: python -m mt5_ea.live.tests.parity ds [SYM ...]
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from mt5_ea.live.core import Frames  # noqa: E402

WS = Path(os.environ.get('WS_ROOT', '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'))


def ws_data(sym):
    w = WS / f'ws_{sym}'
    start = [f for f in os.listdir(w / 'cache') if f.startswith('dowruns_')][0][8:18]
    m = pd.read_csv(w / 'M15_broker.csv', parse_dates=['time']).rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
    return m, pd.Timestamp(start), w / 'research/dow_strategy/results'


def full_frames(sym, m, start):
    """Full-history Frames (slow: Dow runs over many years), cached between test runs."""
    import pickle
    f = WS / 'live_cache' / f'frames_{sym}_{start:%Y%m%d}.pkl'; f.parent.mkdir(exist_ok=True)
    if f.exists():
        return pickle.load(open(f, 'rb'))
    F = Frames(m, start); pickle.dump(F, open(f, "wb")); return F


def compare(mine, ref, last_t, cols=('t', 'side', 'entry', 'sl0', 'exit', 'exit_t')):
    """Research files close still-open trades at the last bar; drop those before comparing."""
    ref = ref.copy(); ref['t'] = pd.to_datetime(ref.t); ref['exit_t'] = pd.to_datetime(ref.exit_t)
    ref = ref[ref.exit_t < last_t].sort_values('t').reset_index(drop=True)
    mine = mine.sort_values('t').reset_index(drop=True) if len(mine) else mine
    n_ok = 0; bad = []
    key = lambda d: {(r.t, int(r.side)): r for r in d.itertuples()}
    A, B = key(mine), key(ref)
    for k in sorted(set(A) | set(B)):
        a, b = A.get(k), B.get(k)
        if a is None or b is None:
            bad.append((k, 'only ported' if b is None else 'only research')); continue
        diff = [c for c in cols if c not in ('t', 'side') and not (
            (getattr(a, c) == getattr(b, c)) if c.endswith('_t') else np.isclose(getattr(a, c), getattr(b, c), atol=1e-9, rtol=0))]
        if diff:
            bad.append((k, 'differs: ' + ','.join(diff)))
        else:
            n_ok += 1
    return n_ok, bad, len(ref)


WINDOW_DAYS = int(os.environ.get('LIVE_WINDOW_DAYS', '600'))   # data the live EA keeps
WARM_DAYS = int(os.environ.get('LIVE_WARM_DAYS', '250'))       # first part: builds the state (Dow, indicators, open positions)
TRADE_DAYS = int(os.environ.get('LIVE_TRADE_DAYS', '150'))     # last part: compared with the full run


def live_frames(m, cut):
    """Frames exactly as the live EA builds them at `cut`: last WINDOW_DAYS of M15 before the cut, trading allowed after
    the warm-up (so positions opened before the compared part exist, as in a full run)."""
    w0 = cut - pd.Timedelta(days=WINDOW_DAYS)
    return Frames(m[(m.t >= w0) & (m.t < cut)], w0 + pd.Timedelta(days=WARM_DAYS), h_days=WARM_DAYS, m_days=WARM_DAYS)


def truncation(fn, m, start, cuts, full=None, detail=False):
    """Test 2, the way the live EA runs. changed = trades of the window run (entered in the last TRADE_DAYS before the cut)
    that differ from or are absent in the full run; missing = full-run trades in that period absent in the window run."""
    if full is None:
        full = fn(Frames(m, start))
    allf = pd.concat([full['trades'], pd.DataFrame(full['open'])], ignore_index=True)
    allf['t'] = pd.to_datetime(allf.t)
    out = []
    for cut in cuts:
        st = cut - pd.Timedelta(days=TRADE_DAYS)
        r = fn(live_frames(m, cut))
        part = pd.concat([r['trades'], pd.DataFrame(r['open'])], ignore_index=True)
        if len(part):
            part['t'] = pd.to_datetime(part.t); part = part[part.t >= st]
        ref = allf[(allf.t >= st) & (allf.t < cut - pd.Timedelta(minutes=15))]
        mis = []
        for p in (part.itertuples() if len(part) else []):
            q = ref[(ref.t == p.t) & (ref.side == p.side)]
            if not len(q) or not np.isclose(q.entry.iat[0], p.entry) or not np.isclose(q.sl0.iat[0], p.sl0):
                mis.append((p.t, p.side, 'absent' if not len(q) else f'sl0 {p.sl0:.6f} vs {q.sl0.iat[0]:.6f}'))
        missing = [(p.t, p.side) for p in ref.itertuples() if not len(part) or not ((part.t == p.t) & (part.side == p.side)).any()]
        if detail and (mis or missing):
            print('   ', f'{cut:%Y-%m-%d}', 'changed', mis[:4], 'missing', missing[:4], flush=True)
        out.append((cut, len(mis), len(missing), len(ref)))
    return out


def fmt2(t2):
    return ' | '.join(f'{c:%Y-%m}: {n} trades, changed {x}, missing {y}' for c, x, y, n in t2)


def cuts_for(m, start, n=12):
    return pd.date_range(start + pd.Timedelta(days=WINDOW_DAYS + 30), m.t.iat[-1], periods=n + 1)[1:]


def run_ds(syms):
    from mt5_ea.live.eas import ds
    for sym in syms:
        m, start, res = ws_data(sym)
        F = full_frames(sym, m, start)
        for stop, ex in (('left', 'tp2'), ('shoulder', 'h1')):
            r = ds.run_variant(F, 'H1', stop, ex, entry_bar=False)
            ref = pd.read_csv(res / 'ds' / f'DS_H1_{stop}_{ex}.csv')
            n_ok, bad, n_ref = compare(r['trades'], ref, F.M15T.iat[-1])
            print(f'[test1] DS {sym} H1 {stop} {ex}: research {n_ref}, same {n_ok}, differ {len(bad)}', bad[:5], flush=True)
        a = ds.ADOPTED[sym]
        fn = lambda F_: ds.run_variant(F_, 'H1', a['stop'], a['exit'])
        print(f'[test2] DS {sym}: ' + fmt2(truncation(fn, m, start, cuts_for(m, start), full=fn(F), detail=True)), flush=True)


def run_m(syms):
    from mt5_ea.live.eas import rsi2
    for sym in syms:
        m, start, res = ws_data(sym)
        a = rsi2.ADOPTED[sym]
        F = full_frames(sym, m, start)
        r = rsi2.run(F, **a)
        ref = pd.read_csv(res / 'rsi2' / f"M_{a['tr']}_{a['lo']}_{a['ex']}_{a['st']}.csv")
        n_ok, bad, n_ref = compare(r['trades'], ref, F.M15T.iat[-1], cols=('t', 'side', 'entry', 'exit', 'exit_t'))
        print(f'[test1] M {sym}: research {n_ref}, same {n_ok}, differ {len(bad)}', bad[:5], flush=True)
        fn = lambda F_: rsi2.run(F_, **a)
        print(f'[test2] M {sym}: ' + fmt2(truncation(fn, m, start, cuts_for(m, start), full=r, detail=True)), flush=True)


def run_q(syms):
    from mt5_ea.live.eas import q
    for sym in syms:
        m, start, res = ws_data(sym)
        a = q.ADOPTED[sym]
        F = full_frames(sym, m, start)
        r = q.run(F, *a, entry_bar=False)
        ref = pd.read_csv(res / 'q' / ('Q_' + '_'.join(map(str, a)) + '.csv'))
        n_ok, bad, n_ref = compare(r['trades'], ref, F.M15T.iat[-1])
        print(f'[test1] Q {sym}: research {n_ref}, same {n_ok}, differ {len(bad)}', bad[:5], flush=True)
        fn = lambda F_: q.run(F_, *a)
        print(f'[test2] Q {sym}: ' + fmt2(truncation(fn, m, start, cuts_for(m, start), full=fn(F), detail=True)), flush=True)


def run_s(syms):
    from mt5_ea.live.eas import s as S_
    for sym in syms:
        m, start, res = ws_data(sym)
        a = S_.ADOPTED[sym]
        F = full_frames(sym, m, start)
        r = S_.run(F, *a, entry_bar=False)
        ref = pd.read_csv(res / 'st2' / ('S_' + '_'.join(a) + '.csv'))
        n_ok, bad, n_ref = compare(r['trades'], ref, F.M15T.iat[-1])
        print(f'[test1] S {sym}: research {n_ref}, same {n_ok}, differ {len(bad)}', bad[:5], flush=True)
        fn = lambda F_: S_.run(F_, *a)
        print(f'[test2] S {sym}: ' + fmt2(truncation(fn, m, start, cuts_for(m, start), full=fn(F), detail=True)), flush=True)


if __name__ == '__main__':
    which = sys.argv[1]; syms = sys.argv[2:]
    {'ds': run_ds, 'm': run_m, 'q': run_q, 's': run_s}[which](syms)
