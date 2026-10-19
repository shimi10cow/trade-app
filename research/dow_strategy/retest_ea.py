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
from env_recognition.data import load as _load  # noqa: E402
from env_recognition import dow_trend as _dt  # noqa: E402
_d1 = _load('D1', 'long'); _d1 = _d1[pd.to_datetime(_d1.t) >= B.START - pd.Timedelta(days=900)].reset_index(drop=True)
RD = _dt.run(_d1, 'D1'); CD = list(pd.to_datetime(_d1.t) + TF_LEN['D1'])
FR = {'H4': (B.h4, B.R4, B.C4, A4), 'H1': (B.h1, B.R1, B.C1, B.A1)}


def events(tf, kinds):
    df, R, C, A = FR[tf]
    out = []
    if 'major' in kinds:
        out += [(C[e['idx']], e['to'], e['broken_price']) for e in R['events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL']
    if 'prov' in kinds:
        out += [(C[e['idx']], e['to'], e.get('broken_price') or (e.get('h2') if e['to'] == 'up' else e.get('l2')))
                for e in R['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
    if 'wq' in kinds:                                   # W filtered to the user's eye (51 labelled H4 Ws, 2026-10-19)
        H, Lo = df.h.to_numpy(float), df.l.to_numpy(float)
        for e in R['w_events']:
            a_, b_ = e['a_anchor'], e['b_anchor']; at = A[a_]; bot = e['action'] == 'W_BOTTOM'
            w0 = max(0, a_ - 90)
            run = (H[w0:a_].max() - e['a']) / at if bot else (e['a'] - Lo[w0:a_].min()) / at
            spd = abs(e['b'] - e['a']) / at / max(1, b_ - a_)
            if spd >= 0.45 and abs(e['a'] - e['c']) / at <= 2 and run >= 6:
                out.append((C[e['idx']], 'up' if bot else 'down', e['b']))
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
            if tf == 'H1' and cfg.get('dir'):
                if cfg['dir'] == 'H4':
                    kk = bisect.bisect_right(B.C4, t) - 1
                    if kk < 0 or B.R4['bars'][kk][0] != d:
                        continue
                else:
                    kk = bisect.bisect_right(CD, t) - 1
                    if kk < 0 or RD['bars'][kk][0] != d:
                        continue
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
                res.append((touch, i1, d, L, tf, i0))
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
    if cfg.get('trig') == 'tl':
        for touch, i1, d, L, tf, i0 in ST:
            k = tl_entry(touch, i1, d, i0)
            if k is not None:
                entries.setdefault(k[0], []).append((d, L, tf, k[1]))
        ST = []
    for touch, i1, d, L, tf, *_ in ST:
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
        for d, L, tf, *ext in entries[i]:
            s = 1 if d == 'up' else -1
            if any(p['side'] == s for p in pos):
                continue
            if cfg.get('ma') and not (s * (B.h1.c.iloc[k1] - S75[k1]) > 0 and s * (S20[k1] - S75[k1]) > 0):
                continue
            swing = ext[0] if ext else B.R15['prov_bars'][i][1]
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
# final M15 Dow pivots with the bar index of the swing and the bar at which it is known
_last = {}
for _e in B.R15['pivot_events']:
    _last[_e['id']] = _e
PIV15 = sorted(((e['idx'], e['kind'], e['price'], e['available_idx']) for e in _last.values()))


def tl_entry(touch, i1, d, i0):
    """User-style correction line: outer tangent from the correction start along the correction's swings.
    Sell setup (d=down): the correction rises -> line under its lows, entry when a close breaks below it.
    Returns (entry signal bar, correction extreme for the stop) or None."""
    s = 1 if d == 'up' else -1
    seg = slice(i0, touch + 1)
    if s == -1:
        a_idx = i0 + int(np.argmin(B.l[seg])); a_p = B.l[a_idx]; kind = 'lo'
    else:
        a_idx = i0 + int(np.argmax(B.h[seg])); a_p = B.h[a_idx]; kind = 'hi'
    cand = [p for p in PIV15 if p[1] == kind and p[0] > a_idx]
    n = len(B.c)
    ext = None
    for k in range(touch, min(i1 + 96, n - 1)):
        ext = max(ext, B.h[k]) if (s == -1 and ext is not None) else (B.h[k] if s == -1 and ext is None else ext)
        if s == 1:
            ext = B.l[k] if ext is None else min(ext, B.l[k])
        known = [p for p in cand if p[3] <= k and p[0] < k]
        if not known:
            continue
        slopes = [(p[2] - a_p) / (p[0] - a_idx) for p in known]
        sl = min(slopes) if s == -1 else max(slopes)
        v = a_p + sl * (k - a_idx)
        if (B.c[k] < v) if s == -1 else (B.c[k] > v):
            return k, ext
    return None


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
    dict(BASE, name='K9 H4主要＋仮転換（Wなし）＋MA', tfs=('H4',), kinds=('major', 'prov'), ma=True),
    dict(BASE, name='K10 K9・1.5R後M15トレール', tfs=('H4',), kinds=('major', 'prov'), ma=True, exit='m15', act=1.5),
    dict(BASE, name='Q1 H4主要＋仮＋良いW＋MA', tfs=('H4',), kinds=('major', 'prov', 'wq'), ma=True),
    dict(BASE, name='Q2 Q1・1.5R後M15トレール', tfs=('H4',), kinds=('major', 'prov', 'wq'), ma=True, exit='m15', act=1.5),
    dict(BASE, name='Q3 良いWのみ＋MA', tfs=('H4',), kinds=('wq',), ma=True),
    dict(BASE, name='Q4 良いWのみ（MAなし）', tfs=('H4',), kinds=('wq',)),
    dict(BASE, name='W1 H1良いW（日足方向）', tfs=('H1',), kinds=('wq',), dir='D1', win=36),
    dict(BASE, name='W2 H1良いW（H4方向）', tfs=('H1',), kinds=('wq',), dir='H4', win=36),
    dict(BASE, name='W3 H1良いW（方向なし）', tfs=('H1',), kinds=('wq',), win=36),
    dict(BASE, name='W4 H1良いW（日足方向）＋MA', tfs=('H1',), kinds=('wq',), dir='D1', win=36, ma=True),
    dict(BASE, name='W5 H1のW全部（日足方向）', tfs=('H1',), kinds=('w',), dir='D1', win=36),
    dict(BASE, name='S0 Q4・余裕0.5', tfs=('H4',), kinds=('wq',), buf=0.5),
    dict(BASE, name='S1 Q4・余裕1.5', tfs=('H4',), kinds=('wq',), buf=1.5),
    dict(BASE, name='S2 Q4・余裕0', tfs=('H4',), kinds=('wq',), buf=0.0),
    dict(BASE, name='X1 Q4・1.5R後M15トレール', tfs=('H4',), kinds=('wq',), exit='m15', act=1.5),
    dict(BASE, name='X2 Q4・固定2R', tfs=('H4',), kinds=('wq',), tp=2.0),
    dict(BASE, name='X3 Q4・固定3R', tfs=('H4',), kinds=('wq',), tp=3.0),
    dict(BASE, name='T1 Q4・戻り待ち120h', tfs=('H4',), kinds=('wq',), win=120),
    dict(BASE, name='T2 Q4・許容0.5ATR', tfs=('H4',), kinds=('wq',), tol=0.5),
    dict(BASE, name='L1 良いW・調整ライン抜けで入る・余裕1.0', tfs=('H4',), kinds=('wq',), trig='tl'),
    dict(BASE, name='L2 L1・固定3R', tfs=('H4',), kinds=('wq',), trig='tl', tp=3.0),
    dict(BASE, name='L3 H4全転換・調整ライン抜け・MA', tfs=('H4',), kinds=('major', 'prov', 'wq'), trig='tl', ma=True),
    dict(BASE, name='L4 L1・余裕0.5', tfs=('H4',), kinds=('wq',), trig='tl', buf=0.5),
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
            if B.START.year < 2015:
                print(f"{name}\n   2005-09 {B.stats(tr.R[(y >= 2005) & (y <= 2009)].to_numpy())}\n   2010-14 {B.stats(tr.R[(y >= 2010) & (y <= 2014)].to_numpy())}"
                      f"\n   2015-19 {B.stats(tr.R[(y >= 2015) & (y <= 2019)].to_numpy())}", flush=True)
            print(f"{name}\n   開発2020-24 {B.stats(tr.R[(y >= 2020) & (y <= 2024)].to_numpy())}"
                  f"\n   確認2025    {B.stats(tr.R[y == 2025].to_numpy())}\n   2026        {B.stats(tr.R[y == 2026].to_numpy())}"
                  f"\n   SL中央値{tr.risk.median() / B.PIP:.0f}pips 保有中央値{((tr.exit_t - tr.t).dt.total_seconds() / 3600).median():.0f}h  {B.recall(tr)}", flush=True)
