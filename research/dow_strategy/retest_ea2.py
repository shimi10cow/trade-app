"""Pattern A, round 2 — rules re-aligned with the user's explanation (2026-10-19):
  * entry is measured two timeframes down: H4 turn -> M15 entry; H1 turn only when it is in the D1 direction
  * a turn = Dow major / provisional reversal, W neck break, or a level touched twice and then broken (close)
  * M15 trigger = the correction's own structure breaks (sell: close below the latest confirmed M15 swing low
    after the retest touch); no need for an M15 Dow reversal
  * stop = beyond the correction extreme since the touch + buf x ATR7(H1), min 10 pips
  * exit = after +1.5R trail to the latest confirmed M15 swing (the user's original rule)
Periods: develop 2020-2024, check 2025, 2026 = model-trade year. Cost 1.2 pip.
Usage: EA_M15_CACHE=<csv> python dow_strategy/retest_ea2.py [config names...]
"""
import bisect
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
import retest_ea as RT  # noqa: E402
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
from env_recognition import dow_trend  # noqa: E402

d1 = load('D1', 'long'); d1 = d1[pd.to_datetime(d1.t) >= B.START - pd.Timedelta(days=900)].reset_index(drop=True)
RD = dow_trend.run(d1, 'D1'); CD = list(pd.to_datetime(d1.t) + TF_LEN['D1'])
M15T = B.T15
P15 = sorted(((M15T[e['available_idx']] + TF_LEN['M15'], e['kind'], e['price']) for e in B.R15['pivot_events']), key=lambda x: x[0])
P15T = [x[0] for x in P15]
S20, S75 = RT.S20, RT.S75


def double_touch_breaks(tf, tol=0.3, maxgap=150):
    """Level touched twice by same-kind confirmed swings (within tol x ATR), then a close beyond it."""
    df, R, C, A = RT.FR[tf]
    piv = sorted(((e['available_idx'], e['kind'], e['price'], e['idx']) for e in R['pivot_events'] if e['action'] == 'confirm'))
    c = df.c.to_numpy(float)
    out, used, known = [], set(), []
    j = 0
    for k in range(len(df)):
        while j < len(piv) and piv[j][0] <= k:
            known.append(piv[j]); j += 1
        for a in range(len(known) - 1, max(-1, len(known) - 12), -1):
            for b in range(a - 1, max(-1, len(known) - 12), -1):
                pa, pb = known[a], known[b]
                if pa[1] != pb[1] or (pa[3], pb[3]) in used or pa[3] - pb[3] < 3 or k - pb[3] > maxgap:
                    continue
                if abs(pa[2] - pb[2]) > tol * A[k]:
                    continue
                L = (pa[2] + pb[2]) / 2
                up = pa[1] == 'hi'
                if (c[k] > L + 0.1 * A[k]) if up else (c[k] < L - 0.1 * A[k]):
                    used.add((pa[3], pb[3]))
                    out.append((C[k], 'up' if up else 'down', L, tf))
    return out


def all_events(cfg):
    ev = []
    for tf, kinds in cfg['src'].items():
        if 'dt' in kinds:
            ev += double_touch_breaks(tf)
        k2 = tuple(x for x in kinds if x != 'dt')
        if k2:
            ev += RT.events(tf, k2)
    out = []
    for t, d, L, tf in ev:
        if tf == 'H1' and cfg.get('h1_d1dir', True):
            kd = bisect.bisect_right(CD, t) - 1
            if kd < 0 or RD['bars'][kd][0] != d:
                continue
        out.append((t, d, L, tf))
    return out


def touches(cfg):
    res = []
    for t, d, L, tf in all_events(cfg):
        df, R, C, A = RT.FR[tf]
        s = 1 if d == 'up' else -1
        k = bisect.bisect_right(C, t) - 1
        band = cfg['tol'] * A[k]
        i0 = M15T.searchsorted(t); i1 = M15T.searchsorted(t + pd.Timedelta(hours=cfg['win']))
        for i in range(i0, min(i1, len(M15T))):
            if s * (B.c[i] - L) < -band:
                break
            if (B.l[i] <= L + band) if s == 1 else (B.h[i] >= L - band):
                res.append((i, i1, d, L, tf)); break
    return res


# small M15 swings (5-bar fractal, known 2 bars later) for the "correction ends" trigger
_FH = [(M15T[i + 2] + TF_LEN['M15'], 'hi', B.h[i]) for i in range(2, len(M15T) - 2)
       if B.h[i] >= max(B.h[i - 2:i]) and B.h[i] > max(B.h[i + 1:i + 3])]
_FL = [(M15T[i + 2] + TF_LEN['M15'], 'lo', B.l[i]) for i in range(2, len(M15T) - 2)
       if B.l[i] <= min(B.l[i - 2:i]) and B.l[i] < min(B.l[i + 1:i + 3])]
F15 = sorted(_FH + _FL, key=lambda x: x[0]); F15T = [x[0] for x in F15]


def last_fractal(ts, kind):
    j = bisect.bisect_right(F15T, ts) - 1
    while j >= 0 and F15[j][1] != kind:
        j -= 1
    return F15[j][2] if j >= 0 else None


def last_swing(ts, kind):
    j = bisect.bisect_right(P15T, ts) - 1
    while j >= 0 and P15[j][1] != kind:
        j -= 1
    return P15[j][2] if j >= 0 else None


def run(cfg):
    TCH = touches(cfg)
    n = len(M15T)
    # build entries: after touch, first close beyond the latest confirmed M15 swing on the trade side
    entries = {}
    for i, i1, d, L, tf in TCH:
        s = 1 if d == 'up' else -1
        ext = B.h[i] if s == -1 else B.l[i]
        for k in range(i, min(i1 + 96, n - 1)):
            ext = max(ext, B.h[k]) if s == -1 else min(ext, B.l[k])
            if s * (B.c[k] - L) < -cfg['tol'] * 3 * B.A1[bisect.bisect_right(B.C1, M15T[k]) - 1]:
                break                                        # fell far back through the level: give up
            sw = (last_fractal if cfg.get('trig') == 'fractal' else last_swing)(M15T[k] + TF_LEN['M15'], 'hi' if s == 1 else 'lo')
            if sw is None:
                continue
            if (B.c[k] > sw) if s == 1 else (B.c[k] < sw):
                entries.setdefault(k, []).append((d, L, tf, ext)); break
    trades, pos = [], []
    for i in range(n):
        keep = []
        for p in pos:
            if p['k'] >= i:
                keep.append(p); continue
            s = p['side']
            if (B.l[i] <= p['sl']) if s == 1 else (B.h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = M15T[i]; trades.append(p); continue
            if not p['trail'] and s * ((B.h[i] if s == 1 else B.l[i]) - p['entry']) >= cfg['act'] * p['risk']:
                p['trail'] = True
            if p['trail'] and cfg.get('exit') == 'h1':
                j = bisect.bisect_right(B.H1PT, M15T[i] + TF_LEN['M15']) - 1
                while j >= 0 and B.H1P[j][1] != ('lo' if s == 1 else 'hi'):
                    j -= 1
                v = B.H1P[j][2] if j >= 0 else None
                if v is not None:
                    v = v - s * B.PIP
                    if (v < B.c[i]) if s == 1 else (v > B.c[i]):
                        p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            elif p['trail']:
                v = last_swing(M15T[i] + TF_LEN['M15'], 'lo' if s == 1 else 'hi')
                if v is not None:
                    v = v - s * B.PIP
                    if (v < B.c[i]) if s == 1 else (v > B.c[i]):
                        p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in entries or i + 1 >= n or M15T[i] < B.START:
            continue
        k1 = bisect.bisect_right(B.C1, M15T[i] + TF_LEN['M15']) - 1
        for d, L, tf, ext in entries[i]:
            s = 1 if d == 'up' else -1
            if any(p['side'] == s for p in pos):
                continue
            if cfg.get('ma') and not (s * (B.h1.c.iloc[k1] - S75[k1]) > 0 and s * (S20[k1] - S75[k1]) > 0):
                continue
            entry = B.o[i + 1]
            if cfg.get('stop') == 'swing':
                sw = B.R15['prov_bars'][i][1]
                ext = sw if sw is not None and ((sw < entry) if s == 1 else (sw > entry)) else ext
            sl = ext - s * cfg['buf'] * B.A1[k1]
            if s * (entry - sl) < 10 * B.PIP:
                sl = entry - s * 10 * B.PIP
            pos.append(dict(k=i + 1, t=M15T[i + 1], side=s, entry=entry, sl=sl, risk=s * (entry - sl), trail=False, src=tf))
    for p in pos:
        p['exit'] = B.c[-1]; p['exit_t'] = M15T[n - 1]; trades.append(p)
    tr = pd.DataFrame(trades)
    tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - B.COST / tr.risk
    return cfg['name'], tr


ALL = ('major', 'prov', 'w', 'dt')
BASE = dict(win=72, tol=0.3, buf=0.5, act=1.5, src={'H4': ALL})
CFGS = [
    dict(BASE, name='S1 H4全転換（2回反発含む）'),
    dict(BASE, name='S2 S1＋H1 MA', ma=True),
    dict(BASE, name='S3 H4全転換＋H1転換(日足方向)', src={'H4': ALL, 'H1': ALL}),
    dict(BASE, name='S4 S3＋H1 MA', src={'H4': ALL, 'H1': ALL}, ma=True),
    dict(BASE, name='S5 S1・余裕1.0', buf=1.0),
    dict(BASE, name='S6 S1・2回反発なし', src={'H4': ('major', 'prov', 'w')}),
    dict(BASE, name='X1 S2・決済だけ1R後H1トレール', ma=True, act=1.0, exit='h1'),
    dict(BASE, name='X2 S2・損切りだけM15仮スイング外＋1.0', ma=True, stop='swing', buf=1.0),
    dict(BASE, name='X3 S2・損切りと決済を1回目と同じに', ma=True, stop='swing', buf=1.0, act=1.0, exit='h1'),
    dict(BASE, name='X4 X3・2回反発なし', ma=True, stop='swing', buf=1.0, act=1.0, exit='h1', src={'H4': ('major', 'prov', 'w')}),
    dict(BASE, name='X5 F2・損切りと決済を1回目と同じに', ma=True, stop='swing', buf=1.0, act=1.0, exit='h1', trig='fractal'),
    dict(BASE, name='X6 S2・損切りだけ余裕1.5', ma=True, buf=1.5),
    dict(BASE, name='F1 S1・小さい高安で入る', trig='fractal'),
    dict(BASE, name='F2 S2・小さい高安で入る', trig='fractal', ma=True),
    dict(BASE, name='F3 S3・小さい高安で入る', trig='fractal', src={'H4': ALL, 'H1': ALL}),
    dict(BASE, name='F4 S4・小さい高安で入る', trig='fractal', src={'H4': ALL, 'H1': ALL}, ma=True),
]

if __name__ == '__main__':
    pick = [c for c in CFGS if not sys.argv[1:] or c['name'].split()[0] in sys.argv[1:]]
    with Pool(4) as pool:
        for name, tr in pool.imap(run, pick):
            y = tr.t.dt.year
            tr.to_csv(B.HERE / 'results' / f"retest2_{name.split()[0]}.csv", index=False)
            print(f"{name}\n   開発2020-24 {B.stats(tr.R[(y >= 2020) & (y <= 2024)].to_numpy())}"
                  f"\n   確認2025    {B.stats(tr.R[y == 2025].to_numpy())}\n   2026        {B.stats(tr.R[y == 2026].to_numpy())}"
                  f"\n   SL中央値{tr.risk.median() / B.PIP:.0f}pips 保有中央値{((tr.exit_t - tr.t).dt.total_seconds() / 3600).median():.0f}h  {B.recall(tr)}", flush=True)
