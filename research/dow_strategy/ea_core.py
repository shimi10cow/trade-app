"""Common EA runner (2026-10-20): setup (where) x trigger (when) x stop x exit, all swappable.

  setup   : list of events dict(t=<time the setup is known>, side=+1/-1, tag=str, [win=hours], [ref=price])
  trigger : M15 bar indices (signal at that bar's close) per direction, e.g. 'dow' (M15 provisional turn),
            'stoch' (existing EA stochastic sequence), or any function registered with add_trigger()
            (the user's M15 MA rule will be plugged in here after the M15 check).
  stop    : 'm15turn' (protected swing of the new M15 provisional trend), 'm15swing' (last confirmed M15 swing),
            'h1swing' (last confirmed H1 swing), 'h1prot' (H1 major protected level), 'h1ma75', 'h1ma200',
            'ref' (the setup's own reference price, e.g. the line or the W low); beyond it by buf x ATR(H1) + pips
  exit    : trail to swings once +act R: 'h1', 'h4', 'm15', or 'hyb' (M15 swings until +sw R, then H1 swings); trail only tightens
Entry at the next M15 open. Cost 1.2 pip. Optional environment filter via env_ctx (dside / env).
Everything uses only information known at the signal bar's close (causal)."""
import bisect, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402  (shared frames + Dow runs, DT_START / DT_CACHE)
import env_ctx as EC  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402

M15T = B.T15; N = len(M15T); L15 = TF_LEN['M15']
CL15 = M15T + L15                                         # close time of each M15 bar

# ---------------------------------------------------------------- triggers
TRIG = {}


def add_trigger(name, fn):
    """fn() -> {'up': sorted M15 indices, 'down': [...]} (signal completes at that bar's close)."""
    TRIG[name] = fn


def _trig_dow():
    prov = [e for e in B.R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
    return {d: sorted(e['idx'] for e in prov if e['to'] == d) for d in ('up', 'down')}


def _trig_stoch(n=14, k=3, dd=5, lo=20, hi=80):
    """Existing EA sequence without its MA filters: K<lo -> K crosses D up -> K crosses lo up (buy); mirror for sell."""
    hh = pd.Series(B.h).rolling(n).max(); ll = pd.Series(B.l).rolling(n).min()
    raw = 100 * (pd.Series(B.c) - ll) / (hh - ll)
    K = raw.rolling(k).mean().to_numpy(); D = pd.Series(K).rolling(dd).mean().to_numpy()
    out = {'up': [], 'down': []}; s1 = s2 = 0
    for i in range(1, N):
        k_, d_, pk, pd_ = K[i], D[i], K[i - 1], D[i - 1]
        if not (np.isfinite(k_) and np.isfinite(d_)):
            continue
        if s1 == 0 and k_ < lo: s1 = 1
        elif s1 == 1 and np.isfinite(pk) and np.isfinite(pd_) and pk <= pd_ and k_ > d_: s1 = 2
        elif s1 == 2 and np.isfinite(pk) and pk <= lo and k_ > lo: s1 = 0; out['up'].append(i)
        if s2 == 0 and k_ > hi: s2 = 1
        elif s2 == 1 and np.isfinite(pk) and np.isfinite(pd_) and pk >= pd_ and k_ < d_: s2 = 2
        elif s2 == 2 and np.isfinite(pk) and pk >= hi and k_ < hi: s2 = 0; out['down'].append(i)
    return out


add_trigger('dow', _trig_dow)
add_trigger('stoch', _trig_stoch)
_TC = {}


def trigger(name):
    if name not in _TC:
        _TC[name] = TRIG[name]()
    return _TC[name]


# ---------------------------------------------------------------- stop references
_last = {}
for _e in B.R15['pivot_events']:
    _last[_e['id']] = _e
P15 = sorted(((M15T[e['available_idx']] + L15, e['kind'], e['price']) for e in B.R15['pivot_events']), key=lambda x: x[0])
P15T = [x[0] for x in P15]
H4P = sorted(((B.C4[e['available_idx']], e['kind'], e['price']) for e in B.R4['pivot_events']), key=lambda x: x[0])
H4PT = [x[0] for x in H4P]
H1MA = {n: B.h1.c.rolling(n).mean().to_numpy() for n in (20, 75, 200)}


def _last_swing(P, PT, ts, kind):
    j = bisect.bisect_right(PT, ts) - 1
    while j >= 0 and P[j][1] != kind:
        j -= 1
    return P[j][2] if j >= 0 else None


def stop_ref(kind, i, s, ev=None):
    """Reference price (before buffer) known at the close of M15 bar i, or None."""
    ts = CL15[i]; k1 = bisect.bisect_right(B.C1, ts) - 1
    want = 'lo' if s == 1 else 'hi'
    if kind == 'm15turn':
        return B.R15['prov_bars'][i][1]
    if kind == 'm15swing':
        return _last_swing(P15, P15T, ts, want)
    if kind == 'h1swing':
        return _last_swing(B.H1P, B.H1PT, ts, want)
    if kind == 'h1prot':
        tr, prot = B.R1['bars'][k1]
        return prot if tr == ('up' if s == 1 else 'down') else None
    if kind in ('h1ma75', 'h1ma200'):
        v = H1MA[int(kind[4:])][k1]
        return v if np.isfinite(v) else None
    if kind == 'ref':
        return None if ev is None else ev.get('ref')
    raise ValueError(kind)


# ---------------------------------------------------------------- linking setups to triggers
def link(events, trig, win=24):
    """First trigger bar in the setup's direction within `win` hours after the setup is known."""
    tg = trigger(trig); out = {}
    for ev in events:
        d = 'up' if ev['side'] == 1 else 'down'
        i0 = CL15.searchsorted(ev['t']); i1 = CL15.searchsorted(ev['t'] + pd.Timedelta(hours=ev.get('win', win)))
        lst = tg[d]; j = bisect.bisect_left(lst, i0)
        if j < len(lst) and lst[j] < i1:
            out.setdefault(lst[j], []).append(ev)
    return out


# ---------------------------------------------------------------- run
def run(events, cfg):
    """cfg: trig, win, stop, buf (x ATR H1), pips, exit ('h1'|'m15'|'hyb'), act, sw, dside/env, one_per_side."""
    ent = link(events, cfg.get('trig', 'dow'), cfg.get('win', 24))
    trades, pos = [], []
    exit_kind, act, sw = cfg.get('exit', 'h1'), cfg.get('act', 1.0), cfg.get('sw', 2.0)
    for i in range(N):
        keep = []
        for p in pos:
            if p['k'] >= i:
                keep.append(p); continue
            s = p['side']
            if (B.l[i] <= p['sl']) if s == 1 else (B.h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = M15T[i]; trades.append(p); continue
            fav = s * ((B.h[i] if s == 1 else B.l[i]) - p['entry'])
            p['mfe'] = max(p['mfe'], fav / p['risk'])
            if not p['trail'] and fav >= act * p['risk']:
                p['trail'] = True
            if p['trail']:
                src = 'h4' if exit_kind == 'h4' else 'h1' if exit_kind == 'h1' or (exit_kind == 'hyb' and p['mfe'] >= sw) else 'm15'
                ts = M15T[i] + L15; want = 'lo' if s == 1 else 'hi'
                v = (_last_swing(H4P, H4PT, ts, want) if src == 'h4' else
                     _last_swing(B.H1P, B.H1PT, ts, want) if src == 'h1' else _last_swing(P15, P15T, ts, want))
                if v is not None:
                    v -= s * B.PIP
                    if (v < B.c[i]) if s == 1 else (v > B.c[i]):
                        p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in ent or i + 1 >= N or M15T[i] < B.START:
            continue
        k1 = bisect.bisect_right(B.C1, CL15[i]) - 1
        for ev in ent[i]:
            s = ev['side']
            if cfg.get('one_per_side', True) and any(p['side'] == s for p in pos):
                continue
            if cfg.get('max_side') and sum(p['side'] == s for p in pos) >= cfg['max_side']:
                continue
            if not EC.env_ok(cfg, CL15[i], s):
                continue
            ref = stop_ref(cfg.get('stop', 'm15turn'), i, s, ev)
            if ref is None:
                continue
            entry = B.o[i + 1]
            sl = ref - s * (cfg.get('buf', 1.0) * B.A1[k1] + cfg.get('pips', 0) * B.PIP)
            if s * (entry - sl) <= 0:
                continue                                  # stop already on the wrong side: no trade
            if s * (entry - sl) < 10 * B.PIP:
                sl = entry - s * 10 * B.PIP
            pos.append(dict(k=i + 1, t=M15T[i + 1], side=s, entry=entry, sl=sl, sl0=sl, risk=s * (entry - sl),
                            trail=False, mfe=0.0, tag=ev.get('tag', ''), setup_t=ev['t']))
    for p in pos:
        p['exit'] = B.c[-1]; p['exit_t'] = M15T[N - 1]; trades.append(p)
    tr = pd.DataFrame(trades)
    if len(tr):
        tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - B.COST / tr.risk
    return tr
