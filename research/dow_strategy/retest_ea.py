"""EA pattern A (user's 'return move', 13 of 22 model trades), 2026-10-19.

Seen in the model trades: shortly before entry a turn happened on H4 (major / provisional Dow reversal or
W top/bottom) or on H1 (mostly W top/bottom), then price came back to the broken level and turned again.

  event   : on TF (H4 or H1) a turn to direction d: major REVERSAL, provisional turn, or W neck break
            level L = the broken swing (reversal) or the W neck (B)
  retest  : within `win` hours price comes back to L (within tol x ATR(TF)) from the d side
            cancelled if a TF bar closes beyond L by more than tol x ATR (break failed)
  trigger : after the touch, the M15 provisional trend turns to d -> entry at next M15 open
  stop    : beyond the M15 swing that made the turn + buf x ATR7(H1), min 10 pips
  exit    : trail to the latest confirmed H1 swing once +1R (as EA #2) | or fixed target
Periods: develop 2020-2024, check 2025, 2026 = model-trade year. Cost 1.2 pip.
Usage: EA_M15_CACHE=<csv> python dow_strategy/retest_ea.py
"""
import bisect
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402  (shared prep: h4/h1/m15 frames, Dow runs, H1 swings, stats, recall)
from env_recognition.pivots import atr  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402

A4 = atr(B.h4)
FR = {'H4': (B.h4, B.R4, B.C4, A4), 'H1': (B.h1, B.R1, B.C1, B.A1)}


def events(tf, kinds):
    df, R, C, _ = FR[tf]
    out = []
    if 'major' in kinds:
        out += [(C[e['idx']], e['to'], e['broken_price']) for e in R['events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL']
    if 'prov' in kinds:
        out += [(C[e['idx']], e['to'], e.get('broken_price') or (e.get('h2') if e['to'] == 'up' else e.get('l2')))
                for e in R['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
    if 'w' in kinds:
        out += [(C[e['idx']], 'up' if e['action'] == 'W_BOTTOM' else 'down', e['b']) for e in R['w_events']]
    return [(t, d, L, tf) for t, d, L in out if L is not None]


M15T = B.T15
M15I = {t: i for i, t in enumerate(M15T)}


def setups(cfg):
    """For every event: the M15 bar index where price first touches the level within the window (or None)."""
    tfs, kinds, win, tol = cfg['tfs'], cfg['kinds'], cfg['win'], cfg['tol']
    res = []
    for tf in tfs:
        df, R, C, A = FR[tf]
        for t, d, L, _ in events(tf, kinds):
            s = 1 if d == 'up' else -1
            k = bisect.bisect_right(C, t) - 1
            band = tol * A[k]
            i0 = M15T.searchsorted(t)                      # first M15 bar after the event bar closed
            i1 = M15T.searchsorted(t + pd.Timedelta(hours=win))
            touch = None
            for i in range(i0, min(i1, len(M15T))):
                if s * (B.c[i] - L) < -band:                 # closed back through the level: failed
                    break
                if (B.l[i] <= L + band) if s == 1 else (B.h[i] >= L - band):
                    touch = i
                    break
            if touch is not None:
                res.append((touch, i1, d, L, tf))
    return res


def run(cfg):
    name = cfg['name']
    ST = setups(cfg)
    prov = B.R15['prov_events']
    turn_idx = {}
    for e in prov:
        if e['action'] in ('REVERSAL', 'PROV_START'):
            turn_idx.setdefault(e['to'], []).append(e['idx'])
    for d in turn_idx:
        turn_idx[d].sort()
    entries = {}
    for touch, i1, d, L, tf in ST:
        lst = turn_idx.get(d, [])
        j = bisect.bisect_left(lst, touch)
        if j < len(lst) and lst[j] < i1 + 96:            # M15 turn after the touch (a little grace after the window)
            k = lst[j]
            entries.setdefault(k, []).append((d, L, tf))
    trades, pos = [], []
    n = len(M15T)
    for i in range(n):
        keep = []
        for p in pos:
            if p['k'] >= i:
                keep.append(p); continue
            s = p['side']
            if (B.l[i] <= p['sl']) if s == 1 else (B.h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = M15T[i]; trades.append(p); continue
            if cfg.get('tp') and ((B.h[i] >= p['tp']) if s == 1 else (B.l[i] <= p['tp'])):
                p['exit'] = p['tp']; p['exit_t'] = M15T[i]; trades.append(p); continue
            if cfg.get('exit') == 'm15':
                if not p['trail'] and s * ((B.h[i] if s == 1 else B.l[i]) - p['entry']) >= cfg.get('act', 1.5) * p['risk']:
                    p['trail'] = True
                if p['trail']:
                    j = bisect.bisect_right(P15T, M15T[i] + TF_LEN['M15']) - 1
                    while j >= 0 and P15[j][1] != ('lo' if s == 1 else 'hi'):
                        j -= 1
                    if j >= 0:
                        v = P15[j][2] - s * B.PIP
                        if (v < B.c[i]) if s == 1 else (v > B.c[i]):
                            p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            elif not cfg.get('tp'):
                if not p['trail'] and s * ((B.h[i] if s == 1 else B.l[i]) - p['entry']) >= p['risk']:
                    p['trail'] = True
                if p['trail']:
                    j = bisect.bisect_right(B.H1PT, M15T[i] + TF_LEN['M15']) - 1
                    while j >= 0 and B.H1P[j][1] != ('lo' if s == 1 else 'hi'):
                        j -= 1
                    if j >= 0:
                        v = B.H1P[j][2] - s * B.PIP
                        if (v < B.c[i]) if s == 1 else (v > B.c[i]):
                            p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in entries or i + 1 >= n or M15T[i] < B.START:
            continue
        k1 = bisect.bisect_right(B.C1, M15T[i] + TF_LEN['M15']) - 1
        for d, L, tf in entries[i]:
            s = 1 if d == 'up' else -1
            if any(p['side'] == s for p in pos):
                continue
            if cfg.get('ma') and not (s * (B.h1.c.iloc[k1] - S75[k1]) > 0 and s * (S20[k1] - S75[k1]) > 0):
                continue
            swing = B.R15['prov_bars'][i][1]
            if swing is None:
                continue
            entry = B.o[i + 1]
            sl = swing - s * cfg['buf'] * B.A1[k1]
            if s * (entry - sl) < 10 * B.PIP:
                sl = entry - s * 10 * B.PIP
            risk = s * (entry - sl)
            p = dict(k=i + 1, t=M15T[i + 1], side=s, entry=entry, sl=sl, risk=risk, trail=False, src=tf)
            if cfg.get('tp'):
                p['tp'] = entry + s * cfg['tp'] * risk
            pos.append(p)
    for p in pos:
        p['exit'] = B.c[-1]; p['exit_t'] = M15T[n - 1]; trades.append(p)
    tr = pd.DataFrame(trades)
    tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - B.COST / tr.risk
    return name, tr


P15 = sorted(((M15T[e['available_idx']] + TF_LEN['M15'], e['kind'], e['price']) for e in B.R15['pivot_events']), key=lambda x: x[0])
P15T = [x[0] for x in P15]
S20 = B.h1.c.rolling(20).mean().to_numpy(); S75 = B.h1.c.rolling(75).mean().to_numpy()
BASE = dict(tfs=('H4', 'H1'), kinds=('major', 'prov', 'w'), win=72, tol=0.3, buf=1.0)
CFGS = [
    dict(BASE, name='R1 H4+H1・全転換・72h・トレール'),
    dict(BASE, name='R2 H4のみ・全転換', tfs=('H4',)),
    dict(BASE, name='R3 H1はWのみ＋H4全転換', tfs=('H4',), extra_h1w=True),
    dict(BASE, name='R4 R1＋H1 MA', ma=True),
    dict(BASE, name='R5 R1・固定2R', tp=2.0),
    dict(BASE, name='R6 R1・固定3R', tp=3.0),
    dict(BASE, name='R7 R1・許容0.5ATR', tol=0.5),
    dict(BASE, name='R8 R1・48h以内', win=48),
    dict(BASE, name='K1 H4主要転換のみ', tfs=('H4',), kinds=('major',)),
    dict(BASE, name='K2 H4仮転換のみ', tfs=('H4',), kinds=('prov',)),
    dict(BASE, name='K3 H4のWのみ', tfs=('H4',), kinds=('w',)),
    dict(BASE, name='K4 H4全転換＋H1 MA', tfs=('H4',), ma=True),
    dict(BASE, name='K5 H4全転換・余裕0.5', tfs=('H4',), buf=0.5),
    dict(BASE, name='K6 K4・1.5R後M15トレール', tfs=('H4',), ma=True, exit='m15', act=1.5),
    dict(BASE, name='K7 K4・1.0R後M15トレール', tfs=('H4',), ma=True, exit='m15', act=1.0),
    dict(BASE, name='K8 K4・2.0R後M15トレール', tfs=('H4',), ma=True, exit='m15', act=2.0),
]


def run_cfg(cfg):
    if cfg.get('extra_h1w'):
        # H4 any turn + H1 W only
        a = dict(cfg, tfs=('H4',)); b = dict(cfg, tfs=('H1',), kinds=('w',))
        global setups_orig
        st = setups(a) + setups(b)
        _orig = globals()['setups']
        globals()['setups'] = lambda c: st
        try:
            return run(cfg)
        finally:
            globals()['setups'] = _orig
    return run(cfg)


if __name__ == '__main__':
    pick = [c for c in CFGS if not sys.argv[1:] or c['name'].split()[0] in sys.argv[1:]]
    with Pool(4) as pool:
        for name, tr in pool.imap(run_cfg, pick):
            y = tr.t.dt.year
            tr.to_csv(B.HERE / 'results' / f"retest_{name.split()[0]}.csv", index=False)
            print(f"{name}\n   開発2020-24 {B.stats(tr.R[(y >= 2020) & (y <= 2024)].to_numpy())}"
                  f"\n   確認2025    {B.stats(tr.R[y == 2025].to_numpy())}\n   2026        {B.stats(tr.R[y == 2026].to_numpy())}"
                  f"\n   SL中央値{tr.risk.median() / B.PIP:.0f}pips 保有中央値{((tr.exit_t - tr.t).dt.total_seconds() / 3600).median():.0f}h  {B.recall(tr)}", flush=True)
