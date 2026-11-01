"""Trend lab (2026-11-01): 1) a daily 'big trend' state, 2) re-entries on H1 pullbacks inside it, 3) long hold.
Simulated on H1 bars (stop checked before target inside a bar = conservative), costs per instrument in price units."""
import sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition.pivots import pivot_events, atr as atr7

DEV = ['EURUSD', 'XAUUSD', 'US500']
OOS = ['GBPUSD', 'USDCAD', 'USDCHF', 'AUDUSD', 'EURJPY', 'CADJPY', 'CHFJPY', 'AUDJPY', 'USDJPY', 'XAGUSD', 'OIL', 'NGAS', 'JP225']
COST = dict(EURUSD=1.2e-4, GBPUSD=1.8e-4, USDCAD=2e-4, USDCHF=1.8e-4, AUDUSD=1.5e-4, USDJPY=0.012, EURJPY=0.02, AUDJPY=0.02, CADJPY=0.025,
            CHFJPY=0.03, XAUUSD=0.35, XAGUSD=0.035, US500=0.6, JP225=10.0, OIL=0.05, NGAS=0.006)

def load(sym):
    h = pd.read_pickle(f'/home/user/trendlab/h1_{sym}.pkl')
    d = h.set_index('t').resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna()
    pc = d.c.shift(); d['atr'] = np.maximum(d.h - d.l, np.maximum((d.h - pc).abs(), (d.l - pc).abs())).rolling(20).mean()
    return h, d

def legs(d, rev=3.0, big=8.0):
    out = []; dirn = 0; st_t = d.index[20]; st = d.c.iloc[20]; ext, ext_t = st, st_t
    for t, r in d.iloc[21:].iterrows():
        a = r.atr
        if dirn == 1 and r.h > ext: ext, ext_t = r.h, t
        if dirn == -1 and r.l < ext: ext, ext_t = r.l, t
        if dirn == 0:
            if r.h > st + rev * a: dirn, ext, ext_t = 1, r.h, t
            elif r.l < st - rev * a: dirn, ext, ext_t = -1, r.l, t
            continue
        if (dirn == 1 and r.l < ext - rev * a) or (dirn == -1 and r.h > ext + rev * a):
            out.append((st_t, ext_t, dirn, st, ext, d.atr.loc[st_t])); st_t, st = ext_t, ext
            dirn = -dirn; ext, ext_t = (r.l, t) if dirn == -1 else (r.h, t)
    L = pd.DataFrame(out, columns=['ts', 'te', 'dir', 'p0', 'p1', 'atr']); L['size'] = (L.p1 - L.p0).abs() / L.atr
    return L[L['size'] >= big].reset_index(drop=True)

# ---------------------------------------------------------------- 1) daily trend state (known at the day's close)
def state(d, kind):
    c = d.c
    if kind == 'don':                                  # 55-day breakout, held until the opposite 20-day extreme
        hi55, lo55 = d.h.rolling(55).max().shift(1), d.l.rolling(55).min().shift(1)
        hi20, lo20 = d.h.rolling(20).max().shift(1), d.l.rolling(20).min().shift(1)
        s = np.zeros(len(d)); cur = 0
        for i in range(len(d)):
            if c.iat[i] > hi55.iat[i]: cur = 1
            elif c.iat[i] < lo55.iat[i]: cur = -1
            elif cur == 1 and c.iat[i] < lo20.iat[i]: cur = 0
            elif cur == -1 and c.iat[i] > hi20.iat[i]: cur = 0
            s[i] = cur
        return pd.Series(s, d.index)
    if kind == 'ma':                                   # above a rising 50-day MA (below a falling one)
        m = c.rolling(50).mean(); up = (c > m) & (m > m.shift(10)); dn = (c < m) & (m < m.shift(10))
        return pd.Series(np.where(up, 1, np.where(dn, -1, 0)), d.index)
    if kind == 'dow':                                  # daily Dow: higher high + higher low (lower / lower)
        ev = pivot_events(d[['o', 'h', 'l', 'c']].reset_index(drop=True)); last = {}; byday = {}
        for e in sorted(ev, key=lambda e: e['available_idx']):
            last[e['id']] = (e['kind'], e['price']); byday[e['available_idx']] = dict(last)
        s = np.zeros(len(d)); snap = {}
        for i in range(len(d)):
            snap = byday.get(i, snap)
            his = [p for k, p in snap.values() if k == 'hi'][-2:]; los = [p for k, p in snap.values() if k == 'lo'][-2:]
            if len(his) == 2 and len(los) == 2:
                s[i] = 1 if his[1] > his[0] and los[1] > los[0] else (-1 if his[1] < his[0] and los[1] < los[0] else 0)
        return pd.Series(s, d.index)
    raise ValueError(kind)

def to_h1(h, s):
    """daily state (decided at the day's close) -> each H1 bar of the FOLLOWING days"""
    day = pd.to_datetime(h.t).dt.normalize()
    return s.shift(1).reindex(day).ffill().fillna(0).to_numpy()

def eval_state(d, L, s):
    det, cov = [], []
    for _, g in L.iterrows():
        x = s[(s.index >= g.ts) & (s.index <= g.te)]
        on = x[x == g.dir]
        cov.append(len(on) / max(1, len(x)))
        det.append((d.c.loc[on.index[0]] - g.p0) * g.dir / abs(g.p1 - g.p0) if len(on) else np.nan)
    inleg = pd.Series(0, s.index)
    for _, g in L.iterrows():
        inleg[(inleg.index >= g.ts) & (inleg.index <= g.te)] = g.dir
    on = s[s != 0]
    return dict(found=np.mean(~np.isnan(det)), lag=np.nanmedian(det), cover=np.mean(cov), precision=np.mean(inleg.loc[on.index] == on))

# ---------------------------------------------------------------- 2) re-entries on H1 pullbacks inside the trend
_EV = {}
def reentry(h, st1, cost, exit_kind='tp2', hl=True, buf=0.3, key=None):
    o, hi, lo, c = (h[z].to_numpy(float) for z in 'ohlc'); T = h.t.to_numpy(); A = atr7(h)
    if key not in _EV or key is None:
        _EV[key] = sorted(pivot_events(h[['o', 'h', 'l', 'c']]), key=lambda e: e['available_idx'])
    ev = _EV[key]
    conf = {}
    for e in ev:
        conf.setdefault(e['available_idx'], []).append(e)
    last = {'hi': [], 'lo': []}; trades = []; pos = None; ids = {}
    for i in range(len(c)):
        for e in conf.get(i, []):                              # pivots known at this bar's close
            ids[e['id']] = (e['kind'], e['price']); last = {'hi': [p for k, p in ids.values() if k == 'hi'], 'lo': [p for k, p in ids.values() if k == 'lo']}
            if pos and exit_kind == 'trail' and pos['on'] and e['kind'] == ('lo' if pos['s'] == 1 else 'hi'):
                ns = e['price'] - pos['s'] * buf * A[i]
                if (ns - pos['sl']) * pos['s'] > 0: pos['sl'] = ns
        if pos:                                                # manage the open trade on this bar
            s = pos['s']; hit_sl = (lo[i] <= pos['sl']) if s == 1 else (hi[i] >= pos['sl'])
            if hit_sl:
                px = min(o[i], pos['sl']) if s == 1 else max(o[i], pos['sl'])
            elif pos['tp'] is not None and ((hi[i] >= pos['tp']) if s == 1 else (lo[i] <= pos['tp'])):
                px = pos['tp']
            else:
                px = None
                if not pos['on'] and ((hi[i] - pos['en']) if s == 1 else (pos['en'] - lo[i])) >= pos['risk']: pos['on'] = True
            if px is not None:
                trades.append(dict(t=T[pos['i']], te=T[i], s=s, en=pos['en'], ex=px, R=(px - pos['en']) * s / pos['risk'] - cost / pos['risk'])); pos = None
            continue
        if not st1[i]:
            continue
        s = int(st1[i]); kind = 'lo' if s == 1 else 'hi'
        new = [e for e in conf.get(i, []) if e['kind'] == kind and e['action'] == 'confirm']
        if not new or len(last[kind]) < 2:
            continue
        p = new[-1]['price']
        if hl and (p - last[kind][-2]) * s <= 0:               # a higher low (lower high): the trend still holds
            continue
        en = c[i]; sl = p - s * buf * A[i]; risk = (en - sl) * s
        if risk <= 0:
            continue
        tp = en + s * 2 * risk if exit_kind == 'tp2' else None
        if exit_kind == 'prev':
            opp = last['hi' if s == 1 else 'lo']; tp = opp[-1] if opp and (opp[-1] - en) * s > 0.5 * risk else en + s * 2 * risk
        pos = dict(i=i, s=s, en=en, sl=sl, risk=risk, tp=tp, on=False)
    return pd.DataFrame(trades)

def stats(tr):
    if not len(tr): return dict(n=0)
    tr = tr.sort_values('te'); eq = tr.R.cumsum(); dd = (eq.cummax().clip(lower=0) - eq).max()
    yrs = (pd.Timestamp(tr.te.max()) - pd.Timestamp(tr.t.min())).days / 365.25
    return dict(n=len(tr), per_y=len(tr) / yrs, win=np.mean(tr.R > 0), avgR=tr.R.mean(), sumR=tr.R.sum(), dd=dd)

def capture(tr, L):
    """share of each big leg captured by the trades entered inside it in its direction (sum of their moves / leg size)"""
    if not len(tr): return np.nan, np.nan
    caps, any_ = [], []
    for _, g in L.iterrows():
        w = tr[(pd.to_datetime(tr.t) >= g.ts) & (pd.to_datetime(tr.t) <= g.te) & (tr.s == g.dir)]
        any_.append(len(w) > 0); caps.append(((w.ex - w.en) * g.dir).sum() / abs(g.p1 - g.p0))
    return np.mean(any_), np.median(caps)

def reentry2(h, st1, cost, exit_kind='trail', depth=2.0, look=20, buf=0.3, key=None):
    """Entry at the end of an H1 pullback: price pulled back >= depth x ATR(H1) from the high of the last `look` bars,
    then an H1 bar closes above the previous bar's high (buy). Stop under the pullback low. Exit: 2R, or H1 swing trail from +1R."""
    o, hi, lo, c = (h[z].to_numpy(float) for z in 'ohlc'); T = h.t.to_numpy(); A = atr7(h)
    if key not in _EV:
        _EV[key] = sorted(pivot_events(h[['o', 'h', 'l', 'c']]), key=lambda e: e['available_idx'])
    conf = {}
    for e in _EV[key]:
        conf.setdefault(e['available_idx'], []).append(e)
    HH = pd.Series(hi).rolling(look).max().to_numpy(); LL = pd.Series(lo).rolling(look).min().to_numpy()
    LO5 = pd.Series(lo).rolling(5).min().to_numpy(); HI5 = pd.Series(hi).rolling(5).max().to_numpy()
    trades = []; pos = None
    for i in range(look + 1, len(c)):
        if pos:
            for e in conf.get(i, []):
                if exit_kind == 'trail' and pos['on'] and e['kind'] == ('lo' if pos['s'] == 1 else 'hi'):
                    ns = e['price'] - pos['s'] * buf * A[i]
                    if (ns - pos['sl']) * pos['s'] > 0: pos['sl'] = ns
            s = pos['s']
            if (lo[i] <= pos['sl']) if s == 1 else (hi[i] >= pos['sl']):
                px = min(o[i], pos['sl']) if s == 1 else max(o[i], pos['sl'])
            elif pos['tp'] is not None and ((hi[i] >= pos['tp']) if s == 1 else (lo[i] <= pos['tp'])):
                px = pos['tp']
            else:
                px = None
                if not pos['on'] and ((hi[i] - pos['en']) if s == 1 else (pos['en'] - lo[i])) >= pos['risk']: pos['on'] = True
            if px is not None:
                trades.append(dict(t=T[pos['i']], te=T[i], s=s, en=pos['en'], ex=px, R=(px - pos['en']) * s / pos['risk'] - cost / pos['risk'])); pos = None
            continue
        s = int(st1[i])
        if not s:
            continue
        if s == 1:
            pulled = HH[i - 1] - LO5[i] >= depth * A[i]; turn = c[i] > hi[i - 1] and c[i] > o[i]; sl = LO5[i] - buf * A[i]
        else:
            pulled = HI5[i] - LL[i - 1] >= depth * A[i]; turn = c[i] < lo[i - 1] and c[i] < o[i]; sl = HI5[i] + buf * A[i]
        if not (pulled and turn):
            continue
        en = c[i]; risk = (en - sl) * s
        if risk <= 0:
            continue
        pos = dict(i=i, s=s, en=en, sl=sl, risk=risk, tp=en + s * 2 * risk if exit_kind == 'tp2' else None, on=False)
    return pd.DataFrame(trades)

def longhold(h, d, sday, cost, k_stop=2.0, k_trail=3.0):
    """Axis 1: enter when the daily state turns on (next day's first H1 open), stop k_stop x ATR(D1), trail k_trail x ATR from the best close,
    exit when the stop is hit or the state turns off."""
    o, hi, lo, c = (h[z].to_numpy(float) for z in 'ohlc'); T = pd.to_datetime(h.t); day = T.dt.normalize().to_numpy()
    sp = sday.shift(1).fillna(0); ATR = d.atr.shift(1)
    first = ~pd.Series(day).duplicated().to_numpy()
    trades = []; pos = None; prev = 0
    for i in range(len(c)):
        if first[i]:
            dd = pd.Timestamp(day[i]); s = int(sp.get(dd, 0)); a = ATR.get(dd, np.nan)
            if pos and (s != pos['s']):                       # the trend is over: out at this open
                px = o[i]; trades.append(dict(t=T[pos['i']], te=T[i], s=pos['s'], en=pos['en'], ex=px, R=(px - pos['en']) * pos['s'] / pos['risk'] - cost / pos['risk'])); pos = None
            if pos and np.isfinite(a):
                pos['best'] = max(pos['best'], c[i - 1]) if pos['s'] == 1 else min(pos['best'], c[i - 1])
                ns = pos['best'] - pos['s'] * k_trail * a
                if (ns - pos['sl']) * pos['s'] > 0: pos['sl'] = ns
            if not pos and s and s != prev and np.isfinite(a):
                en = o[i]; pos = dict(i=i, s=s, en=en, sl=en - s * k_stop * a, risk=k_stop * a, best=en)
            prev = s
        if pos:
            s = pos['s']
            if (lo[i] <= pos['sl']) if s == 1 else (hi[i] >= pos['sl']):
                px = min(o[i], pos['sl']) if s == 1 else max(o[i], pos['sl'])
                trades.append(dict(t=T[pos['i']], te=T[i], s=s, en=pos['en'], ex=px, R=(px - pos['en']) * s / pos['risk'] - cost / pos['risk'])); pos = None
    return pd.DataFrame(trades)
