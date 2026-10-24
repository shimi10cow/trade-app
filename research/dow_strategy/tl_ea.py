"""Trendline EA (user, 2026-10-20): trade the 3rd (or 4th) touch of an IMPULSE trendline on H4 / H1.

Line (user-style, from 76 judged lines): start A = most extreme swing of the previous ULOOK bars; the line is the
outer tangent over the later same-kind Dow swings known so far (it is re-evaluated as swings confirm, causal).
Good-line filter (user judgement): angle >= MIN_ANGLE x ATR per bar (not flat), 2nd-point pullback depth within
DEPTH (about 38-85 %: ~50 % pullbacks give a usable angle), line direction == that TF's major Dow trend (impulse).
Touch = a bar whose low (high) reaches the line (within band x ATR) and closes on the trend side; the next touch
counts only after price moved >= 1 ATR away. Entry: M15 provisional turn in the line direction within `win` h
after the touch bar closed, next M15 open. Stop: beyond the M15 swing + buf x ATR7(H1) (min 10 pips).
Exits (structure based, no fixed R): 'h1' trail H1 swings after +1R | 'm15' trail M15 swings after +1.5R |
'line' close the trade when the line breaks (H4/H1 close) | 'line_m15' both.
Optional regime gate: only when the recent H4 turns / breakouts followed through (regime_gate.py).
Usage: DT_START=2005-01-01 EA_M15_CACHE=<csv> python dow_strategy/tl_ea.py [names]
"""
import os as _os; _ENTRY_BAR = _os.environ.get('EA_ENTRY_BAR') == '1'   # 1 = also check the stop on the entry bar (2026-10-24 fix, §93/§106)
import bisect
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
import env_ctx as EC  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402

ULOOK = {'H4': 20, 'H1': 40}
MAXLEN = 500
A4 = atr(B.h4)
FR = {'H4': (B.h4, B.R4, B.C4, A4), 'H1': (B.h1, B.R1, B.C1, B.A1)}
M15T = B.T15
_last = {}
for _e in B.R15['pivot_events']:
    _last[_e['id']] = _e
P15 = sorted(((M15T[e['available_idx']] + TF_LEN['M15'], e['kind'], e['price']) for e in _last.values()), key=lambda x: x[0])
P15T = [x[0] for x in P15]
# daily-side context: H4 SMA1200 (~ daily SMA200), H4 ER200, known at the H4 close
_c4 = pd.Series(B.h4.c.to_numpy(float))
SMA1200 = _c4.rolling(1200).mean().to_numpy(); SMA200_4 = _c4.rolling(200).mean().to_numpy()
ER200 = (_c4.diff(200).abs() / _c4.diff().abs().rolling(200).sum()).to_numpy()


def ctx_at(t, s):
    k = bisect.bisect_right(B.C4, t) - 1
    return dict(sd=s * (_c4[k] - SMA1200[k]) / A4[k], er=ER200[k], sh=s * (_c4[k] - SMA200_4[k]) / A4[k])


def line_touches(tf, band=0.25):
    """Causal touch events of user-style lines. Returns dicts with close time, direction, touch number, line info."""
    df, R, C, A = FR[tf]
    H, L, Cl = (df[z].to_numpy(float) for z in 'hlc')
    last = {}
    for e in R['pivot_events']:
        last[e['id']] = e
    piv = sorted((e['idx'], e['kind'], e['price'], e['available_idx']) for e in last.values())
    byk = {k: [p for p in piv if p[1] == k] for k in ('hi', 'lo')}
    byk_i = {k: [p[0] for p in v] for k, v in byk.items()}
    n, N = len(df), ULOOK[tf]
    out = []
    for ia, kind, pa, _ in piv:
        up = kind == 'lo'
        j0 = max(0, ia - N)
        if (up and L[j0:ia].size and L[j0:ia].min() < pa) or ((not up) and H[j0:ia].size and H[j0:ia].max() > pa):
            continue
        lo_, hi_ = bisect.bisect_right(byk_i[kind], ia), bisect.bisect_right(byk_i[kind], ia + MAXLEN)
        later = sorted(byk[kind][lo_:hi_], key=lambda p: p[3])
        slope = b = None; q = 0; depth = None; ntouch = 2; away = True; last_touch = None
        for j in range(ia + 1, min(n, ia + MAXLEN)):
            while q < len(later) and later[q][3] <= j:
                pb = later[q]; sl = (pb[2] - pa) / (pb[0] - ia)
                if slope is None or (sl < slope if up else sl > slope):
                    if slope is None:                   # pullback depth at the 2nd point
                        seg = H[ia:pb[0] + 1] if up else L[ia:pb[0] + 1]
                        pk = seg.max() if up else seg.min()
                        depth = (pk - pb[2]) / max(1e-9, pk - pa) if up else (pb[2] - pk) / max(1e-9, pa - pk)
                    slope, b = sl, pb
                q += 1
            if (L[j] < pa) if up else (H[j] > pa):
                break
            if slope is None:
                continue
            v = pa + slope * (j - ia)
            if (Cl[j] < v) if up else (Cl[j] > v):
                out.append(dict(kind='break', t=C[j], d='up' if up else 'down', ia=ia, tf=tf, n=ntouch,
                                angle=abs(slope) / A[ia], depth=depth, trend=R['bars'][j][0]))
                break
            bd = band * A[j]
            if not away and ((L[j] - v) if up else (v - H[j])) > A[j]:
                away = True
            if away and j > b[0] + 1 and ((L[j] <= v + bd) if up else (H[j] >= v - bd)):
                ntouch += 1; away = False
                out.append(dict(kind='touch', t=C[j], d='up' if up else 'down', n=ntouch, ia=ia, tf=tf, v=v,
                                angle=abs(slope) / A[ia], depth=depth, trend=R['bars'][j][0]))
    return out


TOUCH = {tf: line_touches(tf) for tf in FR}
BREAK = {}
for tf in FR:
    for e in TOUCH[tf]:
        if e['kind'] == 'break':
            BREAK[(tf, e['ia'], e['d'])] = e['t']


def last_swing(ts, kind):
    j = bisect.bisect_right(P15T, ts) - 1
    while j >= 0 and P15[j][1] != kind:
        j -= 1
    return P15[j][2] if j >= 0 else None


def run(cfg):
    import regime_gate as RG
    prov = [e for e in B.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
    turns = {'up': sorted(e['idx'] for e in prov if e['to'] == 'up'), 'down': sorted(e['idx'] for e in prov if e['to'] == 'down')}
    entries = {}
    for tf in cfg['tfs']:
        for e in TOUCH[tf]:
            if cfg.get('mode') == 'cbreak':
                # correction line (against that TF's Dow trend) closed through in the trend direction
                if e['kind'] != 'break' or e['trend'] is None or e['trend'] == e['d'] or e['n'] < cfg.get('cb_nmin', 2):
                    continue
                if e['angle'] < cfg.get('cb_angle', 0.0):
                    continue
                dd = e['trend']
                i0 = M15T.searchsorted(e['t']); i1 = M15T.searchsorted(e['t'] + pd.Timedelta(hours=cfg['win']))
                lst = turns[dd]; j = bisect.bisect_left(lst, i0)
                if j < len(lst) and lst[j] < i1:
                    entries.setdefault(lst[j], []).append((dd, None, tf))
                continue
            if e['kind'] != 'touch' or not (cfg['nmin'] <= e['n'] <= cfg['nmax']):
                continue
            if cfg.get('impulse', True) and e['trend'] != e['d']:
                continue
            if e['angle'] < cfg['min_angle'] or e['depth'] is None or not (cfg['depth'][0] <= e['depth'] <= cfg['depth'][1]):
                continue
            if cfg.get('gate'):
                g = RG.regime(e['t'], cfg['gate'])
                if not (g['REVERSAL'] > 0 if cfg.get('gate_kind', 'rev') == 'rev' else g['BREAKOUT'] > 0):
                    continue
            i0 = M15T.searchsorted(e['t']); i1 = M15T.searchsorted(e['t'] + pd.Timedelta(hours=cfg['win']))
            lst = turns[e['d']]; j = bisect.bisect_left(lst, i0)
            if j < len(lst) and lst[j] < i1:
                entries.setdefault(lst[j], []).append((e['d'], BREAK.get((tf, e['ia'], e['d'])), tf))
    trades, pos = [], []
    n = len(M15T)
    for i in range(n):
        keep = []
        for p in pos:
            if p['k'] > i or (p['k'] == i and not _ENTRY_BAR):
                keep.append(p); continue
            s = p['side']
            if (B.l[i] <= p['sl']) if s == 1 else (B.h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = M15T[i]; trades.append(p); continue
            if cfg['exit'] in ('line', 'line_m15') and p['kill'] is not None and M15T[i] + TF_LEN['M15'] > p['kill']:
                p['exit'] = B.c[i]; p['exit_t'] = M15T[i]; p['why'] = 'line'; trades.append(p); continue
            if cfg['exit'] in ('h1', 'm15', 'line_m15', 'hyb'):
                act = cfg.get('act', 1.0 if cfg['exit'] == 'h1' else 1.5)
                fav = s * ((B.h[i] if s == 1 else B.l[i]) - p['entry'])
                p['mfe'] = max(p.get('mfe', 0.0), fav / p['risk'])
                if not p['trail'] and fav >= act * p['risk']:
                    p['trail'] = True
                if p['trail']:
                    if cfg['exit'] == 'h1' or (cfg['exit'] == 'hyb' and p['mfe'] >= cfg.get('sw', 2.0)):
                        j = bisect.bisect_right(B.H1PT, M15T[i] + TF_LEN['M15']) - 1
                        while j >= 0 and B.H1P[j][1] != ('lo' if s == 1 else 'hi'):
                            j -= 1
                        v = B.H1P[j][2] if j >= 0 else None
                    else:
                        v = last_swing(M15T[i] + TF_LEN['M15'], 'lo' if s == 1 else 'hi')
                    if v is not None:
                        v -= s * B.PIP
                        if (v < B.c[i]) if s == 1 else (v > B.c[i]):
                            p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in entries or i + 1 >= n or M15T[i] < B.START:
            continue
        k1 = bisect.bisect_right(B.C1, M15T[i] + TF_LEN['M15']) - 1
        for d, kill, tf in entries[i]:
            s = 1 if d == 'up' else -1
            if any(p['side'] == s for p in pos):
                continue
            if cfg.get('dside') is not None and not ctx_at(M15T[i] + TF_LEN['M15'], s)['sd'] > cfg['dside']:
                continue
            if not EC.env_ok({k: cfg.get(k) for k in ('maxdev', 'notri')}, M15T[i] + TF_LEN['M15'], s):
                continue
            swing = B.R15['prov_bars'][i][1]
            if swing is None:
                continue
            entry = B.o[i + 1]; sl = swing - s * cfg['buf'] * B.A1[k1]
            if s * (entry - sl) < 10 * B.PIP:
                sl = entry - s * 10 * B.PIP
            pos.append(dict(k=i + 1, t=M15T[i + 1], side=s, entry=entry, sl=sl, risk=s * (entry - sl), trail=False, src=tf, kill=kill))
    for p in pos:
        p['exit'] = B.c[-1]; p['exit_t'] = M15T[n - 1]; trades.append(p)
    tr = pd.DataFrame(trades)
    if len(tr):
        tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - B.COST / tr.risk
    return cfg['name'], tr


BASE = dict(tfs=('H4',), nmin=3, nmax=4, min_angle=0.03, depth=(0.3, 0.85), win=24, buf=1.0, exit='h1')
CFGS = [
    dict(BASE, name='T1 H4推進ライン3〜4点目・H1トレール'),
    dict(BASE, name='T2 T1・M15トレール1.5R', exit='m15'),
    dict(BASE, name='T3 T1・ライン割れで決済', exit='line'),
    dict(BASE, name='T4 T1・ライン割れ＋M15トレール', exit='line_m15'),
    dict(BASE, name='T5 H1推進ライン3〜4点目', tfs=('H1',), win=12),
    dict(BASE, name='T6 H4＋H1', tfs=('H4', 'H1')),
    dict(BASE, name='T7 T1・良い線条件なし', min_angle=0.0, depth=(0, 99)),
    dict(BASE, name='T8 T1・3点目のみ', nmax=3),
    dict(BASE, name='T9 T1・5点目以降も', nmax=99),
    dict(BASE, name='D1 T1＋日足側', dside=0),
    dict(BASE, name='D2 T6(H4+H1)＋日足側', tfs=('H4', 'H1'), dside=0),
    dict(BASE, name='D3 T8(3点目のみ)＋日足側', nmax=3, dside=0),
    dict(BASE, name='D4 T9(5点目以降も)＋日足側', nmax=99, dside=0),
    dict(BASE, name='D5 H1のみ＋日足側', tfs=('H1',), win=12, dside=0),
    dict(BASE, name='D6 D2・M15トレール', tfs=('H4', 'H1'), dside=0, exit='m15'),
    dict(BASE, name='D7 D2・良い線条件なし', tfs=('H4', 'H1'), dside=0, min_angle=0.0, depth=(0, 99)),
    dict(BASE, name='D8 D2・3点目以降すべて', tfs=('H4', 'H1'), dside=0, nmax=99),
    dict(BASE, name='S1 D2・待ち12h', tfs=('H4', 'H1'), dside=0, win=12),
    dict(BASE, name='S2 D2・待ち48h', tfs=('H4', 'H1'), dside=0, win=48),
    dict(BASE, name='S3 D2・余裕0.5', tfs=('H4', 'H1'), dside=0, buf=0.5),
    dict(BASE, name='S4 D2・余裕1.5', tfs=('H4', 'H1'), dside=0, buf=1.5),
    dict(BASE, name='S5 D2・角度0.02', tfs=('H4', 'H1'), dside=0, min_angle=0.02),
    dict(BASE, name='S6 D2・角度0.05', tfs=('H4', 'H1'), dside=0, min_angle=0.05),
    dict(BASE, name='S7 D2・押し0.38-0.62', tfs=('H4', 'H1'), dside=0, depth=(0.38, 0.62)),
    dict(BASE, name='S8 D2・押し0.2-1.0', tfs=('H4', 'H1'), dside=0, depth=(0.2, 1.0)),
    dict(BASE, name='S9 D2・日足側2ATR超', tfs=('H4', 'H1'), dside=2),
    dict(BASE, name='S10 D2・推進条件なし', tfs=('H4', 'H1'), dside=0, impulse=False),
    dict(BASE, name='C1 H4調整ライン抜け＋日足側', mode='cbreak', dside=0),
    dict(BASE, name='C2 H1調整ライン抜け＋日足側', mode='cbreak', tfs=('H1',), win=12, dside=0),
    dict(BASE, name='C3 H4+H1調整ライン抜け＋日足側', mode='cbreak', tfs=('H4', 'H1'), dside=0),
    dict(BASE, name='C4 H4調整ライン(3点以上)抜け＋日足側', mode='cbreak', cb_nmin=3, dside=0),
    dict(BASE, name='C5 H4調整ライン抜け（日足条件なし）', mode='cbreak'),
    dict(BASE, name='C6 H1調整ライン(3点以上)抜け＋日足側', mode='cbreak', tfs=('H1',), win=12, cb_nmin=3, dside=0),
    dict(BASE, name='N1 D2＋伸びすぎ除外', tfs=('H4', 'H1'), dside=0, maxdev=3),
    dict(BASE, name='N2 D2＋H4三角の最中は除外', tfs=('H4', 'H1'), dside=0, notri='H4'),
    dict(BASE, name='N3 D2＋両方', tfs=('H4', 'H1'), dside=0, maxdev=3, notri='H4'),
    dict(BASE, name='X1 D2・H1トレール1.5R後', tfs=('H4', 'H1'), dside=0, act=1.5),
    dict(BASE, name='X2 D2・M15トレール1R後', tfs=('H4', 'H1'), dside=0, exit='m15', act=1.0),
    dict(BASE, name='X3 D2・M15→2RからH1', tfs=('H4', 'H1'), dside=0, exit='hyb', act=1.0, sw=2.0),
    dict(BASE, name='X4 D2・M15→3RからH1', tfs=('H4', 'H1'), dside=0, exit='hyb', act=1.0, sw=3.0),
    dict(BASE, name='G1 T1＋相場判定（更新が続く）', gate=40, gate_kind='brk'),
    dict(BASE, name='G2 T1＋相場判定（転換が続く）', gate=40, gate_kind='rev'),
]


def stats(r):
    if not len(r):
        return 'n=0'
    w = r > 0; eq = np.cumsum(r); dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return f"{len(r)}回 {r.sum():+.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} 勝率{w.mean():.0%} DD{dd:.1f}"


if __name__ == '__main__':
    pick = [c for c in CFGS if not sys.argv[1:] or c['name'].split()[0] in sys.argv[1:]]
    with Pool(4) as pool:
        for name, tr in pool.imap(run, pick):
            if not len(tr):
                print(name, 'n=0'); continue
            tr.to_csv(B.HERE / 'results' / f"tl_{name.split()[0]}.csv", index=False)
            y = tr.t.dt.year
            blocks = [(2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026)]
            print(name, '| 全体', stats(tr.R.to_numpy()), flush=True)
            print('   ' + ' / '.join(f"{a % 100:02d}-{b % 100:02d}: {tr.R[(y >= a) & (y <= b)].sum():+.1f}R({((y >= a) & (y <= b)).sum()})" for a, b in blocks), flush=True)
