"""Condition audit (2026-11-03, user): for each live EA, switch off one entry condition at a time and count the trades it
removed (and their R). Live code on the full-history Frames (live_frames_{sym}.pkl). Closed trades from 2005-06 (indices: as data).
Output: audit/a_{sym}.pkl = rows (ea, cond, n_base, n_var, added, added_R list ...).
"""
import bisect
import pickle
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
from mt5_ea.live.env import Env
from mt5_ea.live.eas import c as C_, ds as DS, j2 as J2, l as L_, nt as NT, q as Q, rt as RT, s as S_
from mt5_ea.live.eas.h4gate import gate
from mt5_ea.live.eas.pgate import gate as pgate
from mt5_ea.live.eas.wave import axis_filter
from mt5_ea.live.registry import BY_KEY

sym = sys.argv[1]
F = pickle.load(open(f'/home/user/trendlab/live_frames_{sym}.pkl', 'rb')); env = Env(F.m15_all)
M15 = pd.Timedelta(minutes=15)


def trades(r):
    tr = r['trades']
    if not isinstance(tr, pd.DataFrame) or not len(tr):
        return pd.DataFrame(columns=['t', 'side', 'R'])
    tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]
    x = pd.DataFrame(dict(t=pd.to_datetime(tr[tc]), side=tr.side.astype(int), R=tr.R.astype(float)))
    return x[x.t >= '2005-06-01'].reset_index(drop=True)


# ---- T / T2: rebuild the T1t gate with switches
def t_gates(no=()):
    R1bars = [b[0] for b in F.R1['bars']]; C1 = F.C1

    def h1_ok(t, s):
        k = bisect.bisect_right(C1, t + M15) - 1
        return k >= 0 and R1bars[k] == ('up' if s == 1 else 'down')

    def feat(t, s):
        k = bisect.bisect_right(env.C4, t) - 1
        return dict(er=env.ER[k], side_d=s * (env.cv[k] - env.S1200[k]) / env.A[k])

    def f(t, s):
        if 'h1' not in no and not h1_ok(t, s): return False
        if 'side' not in no and not feat(t, s)['side_d'] > 0: return False
        if 'er' not in no and not feat(t, s)['er'] > 0.10: return False
        if 'tri' not in no and not env.ok({'notri': 'H4'}, t + M15, s): return False
        return True
    import engine_m15 as EM
    return lambda F_, e_: {'T1t': lambda: EM.Config(use_long_ma=False, extra_filter=f), 'R2c': None}


def rt_run(no=()):
    old = RT.gates; RT.gates = t_gates(no)
    try:
        return RT.run(F, 'T1t', env=env)
    finally:
        RT.gates = old


def with_cfg(mod, name, **kw):
    """Run with module-level dict mod.<name> temporarily updated."""
    def call(fn):
        old = getattr(mod, name); setattr(mod, name, dict(old, **kw))
        try:
            return fn()
        finally:
            setattr(mod, name, old)
    return call


def nt_run(no=()):
    saved = dict(M20_MIN=NT.M20_MIN, IMPULSE_MAX=NT.IMPULSE_MAX, OPEN_MAX=NT.OPEN_MAX, SLOPE_MAX=NT.SLOPE_MAX)
    o_ss, o_lev = NT._daily_side_slope, NT._levels
    if 'm20' in no: NT.M20_MIN = -1e9
    if 'imp' in no: NT.IMPULSE_MAX = 1e9
    if 'open' in no: NT.OPEN_MAX = 1e9
    if 'slope4' in no: NT.SLOPE_MAX = 1e9
    if 'side' in no: NT._daily_side_slope = lambda m15: (lambda t, s: True)
    if 'band' in no:
        NT._levels = lambda F_: (lambda f: (lambda t, s: (False, f(t, s)[1])))(o_lev(F_))
    try:
        return NT.run(F, sym)
    finally:
        for k, v in saved.items(): setattr(NT, k, v)
        NT._daily_side_slope, NT._levels = o_ss, o_lev


def ds_run(no=()):
    old = DS.ADOPTED[sym]; oldd = DS.MIN_DEPTH
    a = dict(old)
    if 'ln' in no: a['ln'] = False
    if 'side' in no: a['side'] = None
    DS.ADOPTED[sym] = a
    try:
        return DS.run_adopted(F, sym)
    finally:
        DS.ADOPTED[sym] = old; DS.MIN_DEPTH = oldd


E = {}
if sym == 'EURUSD':
    E['T2@EURUSD'] = [('今', lambda: axis_filter(F, rt_run())), ('H1 のダウ一致', lambda: axis_filter(F, rt_run(('h1',)))),
                      ('日足の向き', lambda: axis_filter(F, rt_run(('side',)))), ('H4 の効率 ER>0.1', lambda: axis_filter(F, rt_run(('er',)))),
                      ('H4 三角なし', lambda: axis_filter(F, rt_run(('tri',)))), ('3 回目の押し（軸）', lambda: rt_run())]
    E['L@EURUSD'] = [('今', lambda: L_.run(F, env=env)), ('3〜4 回目', lambda: L_.run(F, env=env, cfg=dict(L_.N2, nmax=6))),
                     ('角度', lambda: L_.run(F, env=env, cfg=dict(L_.N2, min_angle=0))), ('押しの深さ', lambda: L_.run(F, env=env, cfg=dict(L_.N2, depth=(0, 9)))),
                     ('日足 4ATR（11/3）', lambda: L_.run(F, env=env, cfg=dict(L_.N2, dside=0))), ('日足の向き（全部）', lambda: L_.run(F, env=env, cfg=dict(L_.N2, dside=None))),
                     ('H4 三角なし', lambda: L_.run(F, env=env, cfg=dict(L_.N2, notri=None)))]
    E['C@EURUSD'] = [('今', lambda: pgate(lambda F_, e_: C_.run(F, env=env), 'ext')(F, env)), ('伸びきり（ext）', lambda: C_.run(F, env=env)),
                     ('日足の向き', lambda: pgate(lambda F_, e_: with_cfg(C_, 'CFG', dside=None)(lambda: C_.run(F, env=env)), 'ext')(F, env)),
                     ('H4 SMA75 から 4ATR 以内', lambda: pgate(lambda F_, e_: with_cfg(C_, 'CFG', maxdev=None)(lambda: C_.run(F, env=env)), 'ext')(F, env)),
                     ('H4 三角なし', lambda: pgate(lambda F_, e_: C_.run(F, env=env, notri=False), 'ext')(F, env))]
if sym == 'USDJPY':
    E['C@USDJPY'] = [('今', lambda: gate(lambda F_, e_: C_.run(F, strength=True, notri=False, env=env), 'open')(F, env)),
                     ('H4 の開き', lambda: C_.run(F, strength=True, notri=False, env=env)),
                     ('線の強さ', lambda: gate(lambda F_, e_: C_.run(F, strength=False, notri=False, env=env), 'open')(F, env)),
                     ('日足の向き', lambda: gate(lambda F_, e_: with_cfg(C_, 'CFG', dside=None)(lambda: C_.run(F, strength=True, notri=False, env=env)), 'open')(F, env)),
                     ('H4 SMA75 から 4ATR 以内', lambda: gate(lambda F_, e_: with_cfg(C_, 'CFG', maxdev=None)(lambda: C_.run(F, strength=True, notri=False, env=env)), 'open')(F, env))]
    E['J2@USDJPY'] = [('今', lambda: J2.run(F, **J2.ADOPTED['USDJPY'])), ('H1 の本トレンド一致', lambda: J2.run(F, h1=None, hours=(0, 10))),
                      ('時間帯 0〜10 時', lambda: J2.run(F, h1='h1major', hours=None))]
if sym == 'XAUUSD':
    E['L2@XAUUSD'] = [('今', lambda: L_.run(F, room=1.0, env=env)), ('伸びる先の壁', lambda: L_.run(F, env=env)),
                      ('3〜4 回目', lambda: L_.run(F, room=1.0, env=env, cfg=dict(L_.N2, nmax=6))), ('角度', lambda: L_.run(F, room=1.0, env=env, cfg=dict(L_.N2, min_angle=0))),
                      ('押しの深さ', lambda: L_.run(F, room=1.0, env=env, cfg=dict(L_.N2, depth=(0, 9)))), ('日足 4ATR（11/3）', lambda: L_.run(F, room=1.0, env=env, cfg=dict(L_.N2, dside=0))),
                      ('日足の向き（全部）', lambda: L_.run(F, room=1.0, env=env, cfg=dict(L_.N2, dside=None))), ('H4 三角なし', lambda: L_.run(F, room=1.0, env=env, cfg=dict(L_.N2, notri=None)))]
    E['S@XAUUSD'] = [('今', lambda: S_.run(F, *S_.ADOPTED['XAUUSD'])), ('買いだけ', lambda: S_.run(F, 'ma', 'prov', 'both', 'mt3', 'h1a1'))]
    E['Q@XAUUSD'] = [('今', lambda: Q.run(F, *Q.ADOPTED['XAUUSD'])), ('H1 MA75 の傾き', lambda: Q.run(F, 0.8, 24, 'any', 'now', 'ref', 'h1'))]
    E['DS@XAUUSD'] = [('今', lambda: ds_run()), ('形の幅 24 時間', lambda: ds_run(('ln',))), ('買いだけ', lambda: ds_run(('side',)))]
if sym == 'US30':
    E['T@US30'] = [('今', lambda: pgate(gate(lambda F_, e_: rt_run(), 'open'), 'band')(F, env)), ('水平線で跳ねた直後', lambda: gate(lambda F_, e_: rt_run(), 'open')(F, env)),
                   ('H4 の開き', lambda: pgate(lambda F_, e_: rt_run(), 'band')(F, env)), ('H1 のダウ一致', lambda: pgate(gate(lambda F_, e_: rt_run(('h1',)), 'open'), 'band')(F, env)),
                   ('日足の向き', lambda: pgate(gate(lambda F_, e_: rt_run(('side',)), 'open'), 'band')(F, env)), ('H4 の効率 ER>0.1', lambda: pgate(gate(lambda F_, e_: rt_run(('er',)), 'open'), 'band')(F, env)),
                   ('H4 三角なし', lambda: pgate(gate(lambda F_, e_: rt_run(('tri',)), 'open'), 'band')(F, env))]
    E['Q@US30'] = [('今', lambda: gate(lambda F_, e_: Q.run(F, *Q.ADOPTED['US30']), 'open')(F, env)), ('H4 の開き', lambda: Q.run(F, *Q.ADOPTED['US30'])),
                   ('H1 MA75 の傾き', lambda: gate(lambda F_, e_: Q.run(F, 1.0, 24, 'any', 'dow', 'ref', 'h1'), 'open')(F, env))]
if sym == 'XAGUSD':
    E['Q@XAGUSD'] = [('今', lambda: gate(lambda F_, e_: Q.run(F, *Q.ADOPTED['XAGUSD']), 'open')(F, env)), ('H4 の開き', lambda: Q.run(F, *Q.ADOPTED['XAGUSD']))]
if sym == 'JP225':
    E['DS@JP225'] = [('今', lambda: gate(lambda F_, e_: ds_run(), 'open')(F, env)), ('H4 の開き', lambda: ds_run()), ('形の幅 24 時間', lambda: gate(lambda F_, e_: ds_run(('ln',)), 'open')(F, env))]
if sym == 'US500':
    E['DS@US500'] = [('今', lambda: ds_run()), ('形の幅 24 時間', lambda: ds_run(('ln',))), ('買いだけ', lambda: ds_run(('side',)))]
if sym == 'BTCUSD':
    E['S@BTCUSD'] = [('今', lambda: S_.run(F, *S_.ADOPTED['BTCUSD'])), ('買いだけ', lambda: S_.run(F, 'ma', 'ma', 'both', 'mt3', 'h1a2'))]
if sym in ('EURUSD', 'USDJPY', 'XAUUSD'):
    E[f'P@{sym}'] = [('今', lambda: nt_run()), ('日足の向き＋H1 MA75 の傾き', lambda: nt_run(('side',))), ('水平線で跳ねた直後', lambda: nt_run(('band',))),
                     ('MA20 から深すぎ', lambda: nt_run(('m20',))), ('勢い（6ATR）', lambda: nt_run(('imp',))), ('H4 の開き', lambda: nt_run(('open',)))] + \
                    ([('H4 の傾き', lambda: nt_run(('slope4',)))] if sym in NT.SLOPE_SYMS else [])

rows = []
for ea, vs in E.items():
    base = trades(vs[0][1]()); bk = set(zip(base.t, base.side))
    rows.append(dict(ea=ea, cond='今', n=len(base), R=base.R.tolist(), t=base.t.tolist()))
    for name, fn in vs[1:]:
        try:
            v = trades(fn())
        except Exception as ex:
            print(ea, name, 'ERROR', ex, flush=True); continue
        add = v[[k not in bk for k in zip(v.t, v.side)]]; lost = len(bk - set(zip(v.t, v.side)))
        rows.append(dict(ea=ea, cond=name, n=len(v), R=add.R.tolist(), t=add.t.tolist(), lost=lost, tot_var=float(v.R.sum())))
        print(ea, name, len(base), '->', len(v), 'added', len(add), f'{add.R.mean() if len(add) else 0:+.2f}', flush=True)
pd.to_pickle(rows, f'/home/user/trendlab/audit/a_{sym}.pkl'); print('done', sym, flush=True)
