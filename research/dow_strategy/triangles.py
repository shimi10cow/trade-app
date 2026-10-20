"""Automatic triangles (2026-10-20, from 26 user-drawn triangles).

User view: a triangle = converging highs and lows; one side may be almost flat. In a correction of the trend,
a break in the trend direction tends to run. Wedges (both sides sloping the same way) are tagged separately.

Detection (causal, per time frame, on confirmed Dow swings as they were known at that moment):
  at every swing confirmation take the last two highs (h1 -> h2) and the last two lows (l1 -> l2), alternating,
  all within MAXLEN bars:
    upper falling or flat : h2 <= h1 + FLAT x ATR        lower rising or flat : l2 >= l1 - FLAT x ATR
    at least one side really sloping (|slope| >= MINSL x ATR per bar), start width >= W0 x ATR,
    converging: width at the 4th swing <= SHRINK x width at the start
    shape: 'sym' (upper down, lower up), 'flat_top', 'flat_bottom'; 'wedge_up' / 'wedge_down' when both slope
    the same way (separate, user: judge on its own)
  breakout: first close outside a line after creation (until MAXLEN bars after creation or past the apex)
Outcome for the study: move after the breakout in its direction (ATR of that TF), by the higher-TF Dow direction.
Usage: DT_START=2005-01-01 DT_CACHE=... python dow_strategy/triangles.py [out_dir years...]"""
import bisect, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
from env_recognition.data import load  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402

FLAT, MINSL, W0, SHRINK, MAXLEN = 0.3, 0.01, 3.0, 0.75, 120
_d1 = load('D1', 'long').reset_index(drop=True); _RD = dow_trend.run(_d1, 'D1')
FR = {'M15': (B.m15, B.R15), 'H1': (B.h1, B.R1), 'H4': (B.h4, B.R4), 'D1': (_d1, _RD)}
HIGHER = {'M15': 'H1', 'H1': 'H4', 'H4': 'D1'}


def detect2(tf, nside=3, shrink=0.6, tol=0.25):
    """v2 (closer to the user's triangles): last 3 highs and 3 lows, outer-tangent lines (first and an extreme later
    swing per side, all swings of that side inside the line within tol x ATR), >= 3 touches on at least one side
    (a swing within tol of the line), converged to <= shrink x the start width."""
    df, R = FR[tf]; H, L, C = (df[z].to_numpy(float) for z in 'hlc'); A = atr(df); n = len(df)
    T = pd.to_datetime(df.t)
    cur = {}; out = []; seen = set(); recent = []
    for e in sorted(R['pivot_events'], key=lambda e: (e['available_idx'], e['idx'])):
        cur[e['id']] = (e['idx'], e['kind'], e['price'])
        if e['id'] not in recent:
            recent = (recent + [e['id']])[-24:]
        if e['action'] != 'confirm':
            continue
        j = e['available_idx']
        piv = sorted(cur[i] for i in recent)
        his = [p for p in piv if p[1] == 'hi'][-nside:]; los = [p for p in piv if p[1] == 'lo'][-nside:]
        if len(his) < nside or len(los) < nside:
            continue
        s0 = min(his[0][0], los[0][0]); k = max(his[-1][0], los[-1][0]); a = A[k]
        if not np.isfinite(a) or a <= 0 or k - s0 > MAXLEN:
            continue
        def tangent(P, upper):
            i0, _, p0 = P[0]; best = None
            for i1, _, p1 in P[1:]:
                sl = (p1 - p0) / (i1 - i0)
                if all(((q - (p0 + sl * (iq - i0))) <= tol * a) if upper else ((p0 + sl * (iq - i0)) - q <= tol * a) for iq, _, q in P):
                    best = sl if best is None else (max(best, sl) if upper else min(best, sl))
            return None if best is None else (i0, p0, best)
        U = tangent(his, True); D = tangent(los, False)
        if U is None or D is None:
            continue
        up = lambda x: U[1] + U[2] * (x - U[0]); lo = lambda x: D[1] + D[2] * (x - D[0])
        key = (his[0][0], los[0][0], k)
        if key in seen:
            continue
        w0, wk = (up(s0) - lo(s0)) / a, (up(k) - lo(k)) / a
        if w0 < W0 or wk <= 0 or wk > shrink * w0:
            continue
        tu = sum(abs(q - up(iq)) <= tol * a for iq, _, q in his); td = sum(abs(q - lo(iq)) <= tol * a for iq, _, q in los)
        if max(tu, td) < 3:
            continue
        su, sl = U[2] / a, D[2] / a
        if su > MINSL and sl > MINSL:
            shape = 'wedge_up'
        elif su < -MINSL and sl < -MINSL:
            shape = 'wedge_down'
        elif abs(su) <= MINSL and abs(sl) <= MINSL:
            continue
        elif su > MINSL or sl < -MINSL:
            continue
        else:
            shape = 'flat_top' if abs(su) <= MINSL else 'flat_bottom' if abs(sl) <= MINSL else 'sym'
        seen.add(key)
        bo, end = 0, None
        for x in range(j + 1, min(n, j + MAXLEN)):
            if up(x) - lo(x) <= 0:
                break
            if C[x] > up(x):
                bo, end = 1, x; break
            if C[x] < lo(x):
                bo, end = -1, x; break
        if end is None:
            end = min(n - 1, j + MAXLEN)
        out.append(dict(tf=tf, ih1=U[0], h1=U[1], ih2=k, h2=up(k), il1=D[0], l1=D[1], il2=k, l2=lo(k), created=j, end=end, bo=bo,
                        shape=shape, w0=w0, wk=wk, len=k - s0, touches=int(tu + td), t=T[j], te=T[end]))
    return out


def detect(tf):
    df, R = FR[tf]; H, L, C = (df[z].to_numpy(float) for z in 'hlc'); A = atr(df); n = len(df)
    T = pd.to_datetime(df.t)
    cur = {}; out = []; seen = set(); recent = []
    for e in sorted(R['pivot_events'], key=lambda e: (e['available_idx'], e['idx'])):
        cur[e['id']] = (e['idx'], e['kind'], e['price'])
        if e['id'] not in recent:
            recent = (recent + [e['id']])[-20:]
        if e['action'] != 'confirm':
            continue
        j = e['available_idx']
        piv = sorted(cur[i] for i in recent)[-6:]
        his = [p for p in piv if p[1] == 'hi'][-2:]; los = [p for p in piv if p[1] == 'lo'][-2:]
        if len(his) < 2 or len(los) < 2:
            continue
        (ih1, _, h1), (ih2, _, h2) = his; (il1, _, l1), (il2, _, l2) = los
        s0 = min(ih1, il1); k = max(ih2, il2); a = A[k]
        if not np.isfinite(a) or a <= 0 or k - s0 > MAXLEN or ih2 <= ih1 or il2 <= il1:
            continue
        key = (ih1, ih2, il1, il2)
        if key in seen:
            continue
        su = (h2 - h1) / (ih2 - ih1); sl = (l2 - l1) / (il2 - il1)
        up = lambda x: h1 + su * (x - ih1); lo = lambda x: l1 + sl * (x - il1)
        w0, wk = (up(s0) - lo(s0)) / a, (up(k) - lo(k)) / a
        if w0 < W0 or wk <= 0 or wk > SHRINK * w0:
            continue
        flat_u, flat_l = abs(h2 - h1) <= FLAT * a, abs(l2 - l1) <= FLAT * a
        if su / a > MINSL and sl / a > MINSL:
            shape = 'wedge_up'
        elif su / a < -MINSL and sl / a < -MINSL:
            shape = 'wedge_down'
        elif flat_u and flat_l:
            continue                                         # both flat = a box, not a triangle
        elif h2 > h1 + FLAT * a or l2 < l1 - FLAT * a:
            continue                                         # expanding on one side
        else:
            shape = 'flat_top' if flat_u else 'flat_bottom' if flat_l else 'sym'
        seen.add(key)
        # breakout after creation (bar j is when the 4th swing became known)
        bo, end = 0, None
        apex = s0 + (up(s0) - lo(s0)) / max(1e-12, sl - su) if sl - su > 0 else s0 + 3 * MAXLEN
        for x in range(j + 1, min(n, j + MAXLEN, int(apex) + 1)):
            if C[x] > up(x):
                bo, end = 1, x; break
            if C[x] < lo(x):
                bo, end = -1, x; break
        if end is None:
            end = min(n - 1, j + MAXLEN, int(apex))
        out.append(dict(tf=tf, ih1=ih1, h1=h1, ih2=ih2, h2=h2, il1=il1, l1=l1, il2=il2, l2=l2, created=j, end=end, bo=bo,
                        shape=shape, w0=w0, wk=wk, len=k - s0, t=T[j], te=T[end]))
    return out


def outcome(tf, tri):
    df, R = FR[tf]; H, L, C = (df[z].to_numpy(float) for z in 'hlc'); A = atr(df); n = len(df)
    hf = HIGHER[tf]; dfh, Rh = FR[hf]; Ch = list(pd.to_datetime(dfh.t) + TF_LEN[hf])
    T = pd.to_datetime(df.t); rows = []
    for x in tri:
        if not x['bo']:
            continue
        j, s = x['end'], x['bo']
        if j + 30 >= n:
            continue
        kh = bisect.bisect_right(Ch, T[j] + TF_LEN[tf]) - 1
        ht = Rh['bars'][kh][0] if kh >= 0 else None
        prior = np.sign(C[min(x['ih1'], x['il1'])] - C[max(0, min(x['ih1'], x['il1']) - 2 * x['len'])])
        seg = slice(j + 1, j + 31)
        rows.append(dict(x, f10=s * (C[j + 10] - C[j]) / A[j], f30=s * (C[j + 30] - C[j]) / A[j],
                         mfe=s * ((H[seg].max() if s == 1 else L[seg].min()) - C[j]) / A[j],
                         mae=-s * ((L[seg].min() if s == 1 else H[seg].max()) - C[j]) / A[j],
                         with_higher=ht == ('up' if s == 1 else 'down'), with_prior=prior == s, year=T[j].year))
    return pd.DataFrame(rows)


if __name__ == '__main__':
    pd.set_option('display.width', 220)
    res = {}
    for tf in ('H4', 'H1', 'M15'):
        tri = (detect2 if 'v2' in sys.argv else detect)(tf); d = outcome(tf, tri); res[tf] = (tri, d)
        d.to_csv(B.HERE / 'results' / f"triangles{'2' if 'v2' in sys.argv else ''}_{tf}.csv", index=False)
        d = d[d.year >= 2005]
        print(f'== {tf}: 三角 {len(tri)} 個（抜けあり {len(d)}）', d.shape and d.groupby('shape').size().to_dict())
        d['blk'] = pd.cut(d.year, [2004, 2009, 2014, 2019, 2024, 2026], labels=['05-09', '10-14', '15-19', '20-24', '25-26'])
        for nm, m in (('全部', d.f30 == d.f30), ('上位足と同じ向き', d.with_higher), ('上位足と逆', ~d.with_higher),
                      ('上位足同じ・ウェッジ除く', d.with_higher & ~d['shape'].str.startswith('wedge')), ('ウェッジ', d['shape'].str.startswith('wedge'))):
            x = d[m]
            g = x.groupby('blk', observed=True).f30.mean()
            print(f'   {nm:16s} n={len(x):5d} 10本後{x.f10.mean():+.2f} 30本後{x.f30.mean():+.2f} 最大順行{x.mfe.median():.2f} 最大逆行{x.mae.median():.2f} | '
                  + ' '.join(f'{b}:{v:+.2f}' for b, v in g.items()))
    args = [a for a in sys.argv[1:] if a != 'v2']
    if len(args) > 1:
        outd = Path(args[0]); years = [int(y) for y in args[1:]]
        sec = lambda ts: int((pd.Timestamp(ts) - pd.Timestamp('1970-01-01')) // pd.Timedelta(seconds=1))
        for y in years:
            pay = {}
            for tf, (tri, _) in res.items():
                T = pd.to_datetime(FR[tf][0].t)
                pay[tf] = [[sec(T[x['ih1']]), round(x['h1'], 5), sec(T[x['ih2']]), round(x['h2'], 5), sec(T[x['il1']]), round(x['l1'], 5),
                            sec(T[x['il2']]), round(x['l2'], 5), sec(T[x['created']]), sec(T[x['end']]), x['bo'], x['shape']]
                           for x in tri if T[x['created']].year == y]
            (outd / f'tri_{y}.json').write_text(json.dumps(pay, separators=(',', ':')), encoding='utf-8')
        print('written', years)
