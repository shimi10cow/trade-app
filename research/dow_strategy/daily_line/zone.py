"""Trend entries in the zone near the daily trendline (user idea 2026-11-07). Line = B (daily swings, provisional -> confirmed,
provisional deleted on an H4 close, confirmed on a daily close). A zone visit = H1 bars while the line is alive and the bar's near
side is within ZONE x ATR(D1) of the line (on the trend side, a small H1 pierce allowed); one entry chance per visit, only while
the line is alive. Triggers: M15 Dow turn / H1 Dow turn / M15 correction line break. Stops: the M15 turn swing + 0.5 ATR(H1),
or the farther of that and the line (+0.5 ATR(H1)). Exit: H1 (or H4) swing trail from +1R.
Usage: python zone.py SYMBOL [stage]   stage 1 = zones x triggers (stop far, exit h1), stage 2 = stops x exits for the best"""
import bisect, pickle, sys
import numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
sys.path.insert(0, '/tmp/claude-0/-home-user-trade-app/13978ff6-6519-5f05-b953-f01dd0dd89a9/scratchpad/ana')
from mt5_ea.live import engine as E
from mt5_ea.live.eas import c as C_
from env_recognition import dow_trend
from env_recognition.pivots import atr
import lines_v4 as L4

sym = sys.argv[1]; stage = sys.argv[2] if len(sys.argv) > 2 else '1'
IDX = sym in ('US30', 'US500', 'JP225', 'US100')
F = pickle.load(open(f'/home/user/trendlab/{"idx" if IDX else "tz"}/frames_{sym}.pkl', 'rb'))
m = F.m15_all.set_index('t'); D = m.resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
RD = dow_trend.run(D[['t', 'o', 'h', 'l', 'c']], 'D1'); AD = np.asarray(atr(D), float); TD = pd.to_datetime(D.t)
h4 = F.h4.copy(); h4['t'] = pd.to_datetime(h4.t); h4['day'] = h4.t.dt.normalize(); h4['e'] = h4.t.dt.hour + 4
byday = {d: list(zip(g.e, g.c)) for d, g in h4.groupby('day')}
MAXSPAN = int(sys.argv[5]) if len(sys.argv) > 5 and sys.argv[5] != 'none' else None
D1DEL = len(sys.argv) > 6 and sys.argv[6] == 'd1del'
lines = L4.build(D, RD, AD, 'D1', early=True, h4c=None if D1DEL else [byday.get(d, []) for d in TD.dt.normalize()], maxspan=MAXSPAN)
h1 = F.h1.reset_index(drop=True); T1 = pd.to_datetime(h1.t); C1 = pd.DatetimeIndex(F.C1)
H1h, H1l = h1.h.to_numpy(float), h1.l.to_numpy(float)
dayix = TD.searchsorted(T1, side='right') - 1
frac = ((T1 - TD[np.clip(dayix, 0, None)].values) / pd.Timedelta('1D')).to_numpy()
lval = lambda ln, x: ln['anchor'][1] + ln['slope'] * (x - ln['anchor'][0])

def visits(lo, hi, gap=6, conf_only=False):
    """zone visits: (start time, end time, side, line) with the bar's near side between lo and hi ATR(D1) from the line"""
    out = []
    for ln in lines:
        s = -1 if ln['side'] == -1 else 1
        if conf_only and ln.get('conf') is None: continue
        start_d = max(ln['valid'], ln['conf']) if conf_only else ln['valid']
        j0 = int(np.searchsorted(dayix, start_d + 1, side='left'))      # from the day after the line was drawn (confirmed)
        j1 = int(np.searchsorted(dayix, ln['end'], side='left'))           # until the day the line was deleted (it is dead then)
        cur = None; out_n = 0
        for j in range(j0, j1):
            d = dayix[j]; a = AD[d]
            if not np.isfinite(a) or a <= 0: continue
            v = lval(ln, d + frac[j]); dist = (v - H1h[j]) / a if s == -1 else (H1l[j] - v) / a
            inz = lo - 0.3 <= dist <= hi if lo == 0 else lo <= dist <= hi
            if inz:
                if cur is None: cur = [C1[j], C1[j], s, ln]
                cur[1] = C1[j]; out_n = 0
            elif cur is not None:
                out_n += 1
                if out_n > gap:
                    out.append(tuple(cur)); cur = None
        if cur is not None: out.append(tuple(cur))
    return out

def trig_h1dow(F):
    out = {'up': [], 'down': []}
    for e in F.R1['prov_events']:
        if e['action'] in ('REVERSAL', 'PROV_START'):
            i = int(F.CL15.searchsorted(F.C1[e['idx']]))
            if i < F.N: out[e['to']].append(i)
    return {k: sorted(v) for k, v in out.items()}
def trig_m15tl(F):
    out = {'up': [], 'down': []}
    for ia, pa, ib, pb, cr, en, kind, broken in C_.lines(F)[0]:
        if broken and en is not None: out['up' if kind == 'hi' else 'down'].append(en)
    return {k: sorted(v) for k, v in out.items()}
E.TRIGGERS['h1dow'] = trig_h1dow; E.TRIGGERS['m15tl'] = trig_m15tl
_sr = E.stop_ref
def stop_ref(F_, kind, i, s, ev=None):
    if kind == 'far':
        r = F_.R15['prov_bars'][i][1]
        if r is None or ev is None or ev.get('ln') is None: return r
        ts = F_.CL15[i]; d = int(TD.searchsorted(ts, side='right') - 1); x = d + (ts - TD[d]) / pd.Timedelta('1D')
        v = lval(ev['ln'], x)
        return max(r, v) if s == -1 else min(r, v)
    return _sr(F_, kind, i, s, ev)
E.stop_ref = stop_ref

def evs(V, rearm=None):
    out = []
    for a, b, s, ln in V:
        if rearm is None:
            out.append(dict(t=a, side=int(s), win=max(1.0, (b - a) / pd.Timedelta('1h') + 1), tag='z', ln=ln))
        else:                                   # one entry chance per `rearm` hours while in the zone
            t = a
            while t <= b:
                out.append(dict(t=t, side=int(s), win=min(rearm, max(1.0, (b - t) / pd.Timedelta('1h') + 1)), tag='z', ln=ln)); t += pd.Timedelta(hours=rearm)
    return out
def st(R):
    R = np.asarray(R); n = len(R)
    if n < 5: return f'{n:3d}件'
    t = R.mean() / R.std() * np.sqrt(n); eq = R.cumsum(); dd = (np.maximum.accumulate(eq) - eq).max(); h = n // 2
    return f'{n:4d}件 勝率{(R > 0).mean():3.0%} 平均{R.mean():+.2f}R 合計{R.sum():+6.1f} DD{dd:5.1f} t{t:+.2f} 前後{R[:h].mean():+.2f}/{R[h:].mean():+.2f}'
def run(V, trig, stop, ex, rearm=None, stack=None):
    cfg = dict(trig='dow' if trig == 'm15dow' else trig, stop=stop, buf=0.5, exit=ex, act=1.0, one_per_side=True)
    if stack: cfg.pop('one_per_side'); cfg['stack'] = stack
    tr = E.run(F, evs(V, rearm), cfg)['trades']
    if not len(tr): return tr
    tr = tr.copy(); tr['t'] = pd.to_datetime(tr.t); return tr[tr.t >= '2005-06-01'].sort_values('t')

TN = {'m15dow': 'M15ダウ転換', 'h1dow': 'H1ダウ転換', 'm15tl': 'M15調整ライン抜け'}
Z = {'0-0.5ATR': (0, 0.5), '0-1.0ATR': (0, 1.0), '0-1.5ATR': (0, 1.5), '比較 2-4ATR離れ': (2.0, 4.0)}
def trig_dowma(F, mode):
    h1c = F.h1.c.to_numpy(float); S20, S75 = F.H1MA[20], F.H1MA[75]; C1l = list(F.C1)
    base = E._trigger(F, 'dow'); out = {}
    for d, lst in base.items():
        s = 1 if d == 'up' else -1; keep = []
        for i in lst:
            k = bisect.bisect_right(C1l, F.CL15[i]) - 1
            if k < 3: continue
            p20 = (h1c[k] - S20[k]) * s > 0; sl20 = (S20[k] - S20[k - 3]) * s > 0; al = (S20[k] - S75[k]) * s > 0
            p75 = (h1c[k] - S75[k]) * s > 0
            ok = {'p20sl': p20 and sl20, 'p20': p20, 'al': al, 'p20al': p20 and al, 'p20slal': p20 and sl20 and al, 'p20slp75': p20 and sl20 and p75}[mode]
            if ok: keep.append(i)
        out[d] = keep
    return out
for _m in ('p20sl', 'p20', 'al', 'p20al', 'p20slal', 'p20slp75'):
    E.TRIGGERS['dowma_' + _m] = (lambda mm: (lambda F_: trig_dowma(F_, mm)))(_m)
def run2(V, trig, stop, ex, act):
    cfg = dict(trig=trig, stop=stop, buf=0.5, exit=ex, act=act, sw=2.0, one_per_side=True)
    tr = E.run(F, evs(V), cfg)['trades']
    if not len(tr): return tr
    tr = tr.copy(); tr['t'] = pd.to_datetime(tr.t); return tr[tr.t >= '2005-06-01'].sort_values('t')
# exit 'h1m15': trail H1 swings from act, switch to M15 swings once the trade has run sw R (user, 2026-11-07)
import inspect as _insp
_src = _insp.getsource(E.run)
_a = "src = 'h4' if xk == 'h4' else 'm15' if xk == 'm15' else"
assert _a in _src
_src = _src.replace(_a, "src = 'm15' if (exit_kind == 'h1m15' and p['mfe'] >= sw) else 'h1' if exit_kind == 'h1m15' else 'h4' if xk == 'h4' else 'm15' if xk == 'm15' else")
# exit 'h1x': H1 trail from act; once the H1 SMA20/75 cross (trade way) with SMA75 sloping the trade way appears AFTER the entry,
# trail H4 swings instead (a new H1 trend started: hold it)
_b = "            if not p['trail'] and fav >= act * p['risk']:"
assert _b in _src
_src = _src.replace(_b, '''            if exit_kind == 'h1x':
                _k = bisect.bisect_right(F.C1, F.CL15[i]) - 1
                _c = (F.H1MA[20][_k] - F.H1MA[75][_k]) * s > 0 and (F.H1MA[75][_k] - F.H1MA[75][_k - 5]) * s > 0
                if 'x0' not in p: p['x0'] = _c
                if _c and not p['x0']: p['long'] = True
''' + _b)
_src = _src.replace("src = 'm15' if (exit_kind == 'h1m15'", "src = 'h4' if p.get('long') else 'h1' if exit_kind == 'h1x' else 'm15' if (exit_kind == 'h1m15'")
exec(compile(_src, 'engine_run_patch', 'exec'), E.__dict__)
if stage == 'J':
    V = visits(0, 0.5, conf_only=False)
    S20, S75 = F.H1MA[20], F.H1MA[75]; h1c = F.h1.c.to_numpy(float); A1 = F.A1
    def cls(t, s):
        k = bisect.bisect_right(F.C1, pd.Timestamp(t)) - 1
        al = (S20[k] - S75[k]) * s > 0; s75 = (S75[k] - S75[k - 10]) * s
        n = 0
        while al and k - n > 0 and (S20[k - n] - S75[k - n]) * s > 0: n += 1
        if s75 < 0: return 'B: SMA75 が逆向き'
        if al and n >= 48: return 'A: クロス済み・48本以上進んだ'
        return 'C: クロス前/直後'
    X = [('今 H1 +1Rから', dict(exit='h1', act=1.0)), ('H1 +0.5Rから', dict(exit='h1', act=0.5)), ('M15 +1Rから', dict(exit='m15', act=1.0)),
         ('M15 +0.5Rから', dict(exit='m15', act=0.5)), ('利確 1.5R', dict(exit='h1', act=99, tp=1.5)), ('利確 2R', dict(exit='h1', act=99, tp=2.0))]
    res = {}
    for nm, kw in X:
        cfg = dict(trig='dowma_p20sl', stop='far', buf=0.5, sw=2.0, one_per_side=True); cfg.update(kw)
        tr = E.run(F, evs(V), cfg)['trades']; tr = tr.copy(); tr['t'] = pd.to_datetime(tr.t); tr = tr[tr.t >= '2005-06-01']
        tr['cls'] = [cls(t, s) for t, s in zip(tr.t, tr.side)]; res[nm] = tr.set_index(['t', 'side'])
    pd.to_pickle(res, f'/home/user/trendlab/check/zoneJ_{sym}.pkl')
    base = res['今 H1 +1Rから']
    for c in sorted(base.cls.unique()):
        print(f'{sym} [{c}] 今の件数 {int((base.cls == c).sum())}', flush=True)
        for nm, _ in X:
            r = res[nm]; R = r.R[r.cls == c].values
            print(f'{sym}    {nm:14s} {st(R)}', flush=True)
    sys.exit()
if stage == 'I':
    V = visits(0, 0.5, conf_only=False)
    tr = run2(V, 'dowma_p20sl', 'far', 'h1', 1.0)
    pd.to_pickle(tr, f'/home/user/trendlab/check/final_{sym}.pkl'); print(sym, len(tr), round(tr.R.sum(), 1), flush=True)
    sys.exit()
if stage == 'H':
    def runx(V, rearm=None, maxside=None):
        cfg = dict(trig='dowma_p20sl', stop='far', buf=0.5, exit='h1', act=1.0, one_per_side=True)
        if maxside: cfg.pop('one_per_side'); cfg['max_side'] = maxside
        evx = []
        for a, b, s_, ln in V:
            if rearm is None:
                evx.append(dict(t=a, side=int(s_), win=max(1.0, (b - a) / pd.Timedelta('1h') + 1), tag=f'{a}', ln=ln)); continue
            t = a
            while t <= b:
                evx.append(dict(t=t, side=int(s_), win=min(rearm, max(1.0, (b - t) / pd.Timedelta('1h') + 1)), tag=f'{a}', ln=ln)); t += pd.Timedelta(hours=rearm)
        tr = E.run(F, evx, cfg)['trades']; tr = tr.copy(); tr['t'] = pd.to_datetime(tr.t); return tr[tr.t >= '2005-06-01'].sort_values('t')
    lab = '仮ラインは日足終値で消す' if D1DEL else '仮ラインはH4終値で消す'
    for zw in (0.5, 0.75):
        V = visits(0, zw, conf_only=False)
        for nm, rearm, ms in (('エリアごと1回', None, None), ('12時間ごとに再エントリー・同時2つまで', 12, 2), ('6時間ごと・同時2つまで', 6, 2)):
            tr = runx(V, rearm, ms); first = ~tr.duplicated('tag')
            print(f'{sym} {lab} エリア{zw}ATR {nm:22s} {st(tr.R)} | 1回目 {st(tr.R[first])} | 2回目以降 {st(tr.R[~first])}', flush=True)
    sys.exit()
if stage == 'G':
    import collections
    V = visits(0, 0.5, conf_only=False)
    # per line: the order of its zone visits (1 = the first visit after the line was drawn = the 3rd touch)
    cnt = collections.Counter(); order = {}
    for a, b, s_, ln in sorted(V, key=lambda v: v[0]):
        key = id(ln['anchor']) if False else (ln['anchor'], ln['slope'])
        cnt[key] += 1; order[(a, s_)] = cnt[key]
    from mt5_ea.live.eas.j2 import h4_legs
    L4g = h4_legs(F)
    def dlegs():
        n_ = len(RD['bars']); tr__ = [b[0] for b in RD['bars']]; lg = np.zeros(n_, int); evd = {}
        for e in RD['events']:
            if e.get('machine') == 'major' and e['action'] in ('BREAKOUT', 'REVERSAL'): evd.setdefault(e['idx'], []).append(e['action'])
        c_ = 0
        for k in range(n_):
            for a_ in evd.get(k, []): c_ = 1 if a_ == 'REVERSAL' else c_ + 1
            if k > 0 and tr__[k] != tr__[k - 1] and 'REVERSAL' not in evd.get(k, []): c_ = 1
            lg[k] = c_
        return lambda t, s: (lambda k: int(lg[k]) if k >= 0 and tr__[k] == ('up' if s == 1 else 'down') else 0)(int(TD.searchsorted(t, side='right') - 2))
    DLg = dlegs()
    def show(name, tr):
        print(f'{sym} {name:34s} {st(tr.R) if len(tr) else "0件"}', flush=True)
    base = run2(V, 'dowma_p20sl', 'far', 'h1', 1.0); show('今（H1 +1Rから）', base)
    show('決済: H1、エントリー後にH1クロス+75傾き→H4', run2(V, 'dowma_p20sl', 'far', 'h1x', 1.0))
    # visit order / trend stage on the base trades
    o = np.array([order.get((pd.Timestamp(t), int(s)), 0) for t, s in zip(base.setup_t, base.side)])
    for k, nm in ((1, '1回目のエリア（3点目）'), (2, '2回目（4点目）'), (3, '3回目以降')):
        c = (o == k) if k < 3 else (o >= 3); show('  ' + nm, base[c])
    h4 = np.array([L4g(pd.Timestamp(t), int(s)) for t, s in zip(base.t, base.side)]); d1 = np.array([DLg(pd.Timestamp(t), int(s)) for t, s in zip(base.t, base.side)])
    for nm, c in (('  H4ダウ 逆向き/1-2段目', h4 <= 2), ('  H4ダウ 3段目以降', h4 >= 3), ('  日足ダウ 逆向き/1-2段目', d1 <= 2), ('  日足ダウ 3段目以降', d1 >= 3)):
        show(nm, base[c])
    # additional entries: re-arm every 12 h inside the zone visit, up to 2 positions (the 2nd only while the 1st trails) / or no overlap
    for nm, stack in (('追加エントリー: 12時間ごと・重ならない', None), ('追加エントリー: 12時間ごと・同時2つ', 2)):
        cfg = dict(trig='dowma_p20sl', stop='far', buf=0.5, exit='h1', act=1.0, one_per_side=True)
        if stack: cfg.pop('one_per_side'); cfg['stack'] = stack
        evx = []
        for a, b, s_, ln in V:
            t = a; j = 0
            while t <= b:
                evx.append(dict(t=t, side=int(s_), win=min(12, max(1.0, (b - t) / pd.Timedelta('1h') + 1)), tag=f'{a}', ln=ln)); t += pd.Timedelta(hours=12); j += 1
        tr = E.run(F, evx, cfg)['trades']; tr = tr.copy(); tr['t'] = pd.to_datetime(tr.t); tr = tr[tr.t >= '2005-06-01'].sort_values('t')
        first = ~tr.duplicated('tag'); show(nm, tr); show('   その中の 1回目', tr[first]); show('   その中の 2回目以降', tr[~first])
    sys.exit()
if stage == 'F':
    V = visits(0, 0.5, conf_only=False)
    zt = run2(V, 'dowma_p20sl', 'far', 'h1', 1.0)
    tr_ = [b[0] for b in RD['bars']]; base = []
    for d in range(1, len(D)):
        if tr_[d] in ('up', 'down'):
            base.append((TD[d] + pd.Timedelta('1D'), TD[d] + pd.Timedelta('2D'), 1 if tr_[d] == 'up' else -1, None))
    cfg = dict(trig='dowma_p20sl', stop='m15turn', buf=0.5, exit='h1', act=1.0, one_per_side=True)
    bt = E.run(F, [dict(t=a, side=s, win=24, tag='b') for a, b, s, _ in base], cfg)['trades']
    bt = bt.copy(); bt['t'] = pd.to_datetime(bt.t); bt = bt[bt.t >= '2005-06-01']
    zt2 = run2(V, 'dowma_p20sl', 'm15turn', 'h1', 1.0)
    pd.to_pickle(dict(zone=zt, zone_m15stop=zt2, base=bt), f'/home/user/trendlab/check/zoneF_{sym}.pkl')
    print(sym, 'zone', st(zt.R), '| base', st(bt.R), flush=True)
    sys.exit()
if stage == 'E':
    V = visits(0, 0.5, conf_only=False)
    X = [('H1 +1Rから（今）', dict(exit='h1', act=1.0)), ('H1 +1.5Rから', dict(exit='h1', act=1.5)),
         ('H1→+2RでM15', dict(exit='h1m15', act=1.0, sw=2.0)), ('H1→+3RでM15', dict(exit='h1m15', act=1.0, sw=3.0)), ('H1→+4RでM15', dict(exit='h1m15', act=1.0, sw=4.0)),
         ('H1(+1.5R)→+3RでM15', dict(exit='h1m15', act=1.5, sw=3.0)),
         ('H4 +1Rから', dict(exit='h4', act=1.0)), ('M15 +1Rから', dict(exit='m15', act=1.0)), ('利確 3R', dict(exit='h1', act=99, tp=3.0))]
    for nm, kw in X:
        cfg = dict(trig='dowma_p20sl', stop='far', buf=0.5, sw=2.0, one_per_side=True); cfg.update(kw)
        tr = E.run(F, evs(V), cfg)['trades']; tr = tr.copy(); tr['t'] = pd.to_datetime(tr.t); tr = tr[tr.t >= '2005-06-01'].sort_values('t')
        print(f'{sym} 決済={nm:20s} {st(tr.R)}', flush=True)
    sys.exit()
if stage == 'D':
    V = visits(0, 0.5, conf_only=False); out = {}
    for mode, nm in (('p20sl', '今: 終値SMA20順側+SMA20順向き'), ('p20slal', '+ SMA20/75 の並び（クロス後）'), ('p20slp75', '+ 終値が SMA75 の順側')):
        tr = run2(V, 'dowma_' + mode, 'far', 'h1', 1.0); out[mode] = tr
        print(f'{sym} {nm:30s} {st(tr.R)}', flush=True)
    pd.to_pickle(out, f'/home/user/trendlab/check/zoneD_{sym}.pkl')
    sys.exit()
if stage == 'C':
    for co, lab in ((True, '確定ラインだけ'), (False, '仮ラインも')):
        V0 = visits(0, 0.5, conf_only=co)
        for ext in (0, 24):
            V = [(a, b + pd.Timedelta(hours=ext), s, ln) for a, b, s, ln in V0]
            for ex, act, nm in (('h1', 1.0, 'H1 +1Rから'), ('h1', 1.5, 'H1 +1.5Rから'), ('h1', 2.0, 'H1 +2Rから'), ('m15', 1.0, 'M15 +1Rから'), ('hyb', 1.0, 'M15→+2RでH1')):
                tr = run2(V, 'dowma_p20sl', 'far', ex, act)
                print(f'{sym} {lab} 延長{ext:2d}h 決済={nm:12s} {st(tr.R) if len(tr) else "0件"}', flush=True)
    sys.exit()
if stage == 'B':
    V0 = visits(0, 0.5, conf_only=True)
    for ext in (0, 24, 48):
        V = [(a, b + pd.Timedelta(hours=ext), s, ln) for a, b, s, ln in V0]
        for mode, nm in (('p20sl', 'H1終値SMA20順側+SMA20順向き'), ('p20', 'H1終値SMA20順側'), ('al', 'H1 MA20/75そろう')):
            for stop in ('far', 'm15turn'):
                tr = run(V, 'dowma_' + mode, stop, 'h1')
                print(f'{sym} 延長{ext:2d}h {nm:22s} 損切り={stop:7s} {st(tr.R) if len(tr) else "0件"}', flush=True)
    sys.exit()
if stage == 'A':
    V = visits(0, 0.5, conf_only=True)
    h1c = F.h1.c.to_numpy(float); S20, S75 = F.H1MA[20], F.H1MA[75]
    def maf(tr):
        rows = []
        for x in tr.itertuples():
            t = pd.Timestamp(x.t); k = bisect.bisect_right(F.C1, t) - 1; s = x.side
            rows.append(dict(al=np.sign(S20[k] - S75[k]) * s, p20=np.sign(h1c[k] - S20[k]) * s, sl20=np.sign(S20[k] - S20[k - 3]) * s,
                             p75=np.sign(h1c[k] - S75[k]) * s))
        return pd.DataFrame(rows, index=tr.index)
    out = {}
    for trig in ('m15dow', 'm15tl', 'stoch'):
        for stop in ('m15turn', 'far', 'h1ma75'):
            tr = run(V, trig, stop, 'h1')
            if not len(tr): print(sym, trig, stop, '0件'); continue
            f = maf(tr); out[(trig, stop)] = (tr, f)
            print(f'{sym} {trig:6s} 損切り={stop:7s} 全部 {st(tr.R)}', flush=True)
            for nm, c in (('H1 MA20/75 そろう', f.al > 0), ('H1 終値がSMA20の順側', f.p20 > 0), ('H1 SMA20 が順向き', f.sl20 > 0),
                          ('終値SMA20順側+SMA20順向き', (f.p20 > 0) & (f.sl20 > 0)), ('H1 終値がSMA75の順側', f.p75 > 0)):
                print(f'{"":30s} {nm:20s} {st(tr.R[c])} | それ以外 {st(tr.R[~c])}', flush=True)
    pd.to_pickle(out, f'/home/user/trendlab/check/zoneA_{sym}.pkl')
    sys.exit()
if stage == '3':
    for name, co, rearm, stack, ex in (('今（全ライン・1回）', False, None, None, 'h1'), ('確定ラインだけ', True, None, None, 'h1'),
                                     ('確定 + 1日1回まで・同時2つ', True, 24, 2, 'h1'), ('確定 + 1日1回まで・同時3つ', True, 24, 3, 'h1'),
                                     ('確定 + 決済H4', True, None, None, 'h4'), ('確定 + 1日1回・同時2つ + 決済H4', True, 24, 2, 'h4')):
        V = visits(0, 0.5, conf_only=co); tr = run(V, 'm15dow', 'far', ex, rearm, stack)
        print(f'{sym} span={MAXSPAN} {name:28s} {st(tr.R) if len(tr) else "0件"}', flush=True)
    sys.exit()
if stage == '1':
    for zn, (lo, hi) in Z.items():
        V = visits(lo, hi)
        for trig in ('m15dow', 'h1dow', 'm15tl'):
            tr = run(V, trig, 'far', 'h1')
            print(f'{sym} {zn:14s} {TN[trig]:10s} エリア{len(V):4d}回 {st(tr.R) if len(tr) else "0件"}', flush=True)
else:
    lo, hi = Z[sys.argv[3]]; trig = sys.argv[4]; V = visits(lo, hi)
    for stop in ('m15turn', 'far'):
        for ex in ('h1', 'h4'):
            tr = run(V, trig, stop, ex)
            print(f'{sym} {sys.argv[3]} {TN[trig]} 損切り={"M15転換点" if stop == "m15turn" else "M15とライン遠い方"} 決済={ex}: {st(tr.R)}', flush=True)
