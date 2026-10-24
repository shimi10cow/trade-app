"""Swing-based pullback counter fitted to the user's labels (2026-10-22).
A pullback is counted when, after the trend has made a new extreme, a swing low (buy) / swing high (sell) forms:
the bar that is the lowest of the `par` bars on each side (confirmed `par` bars later), at least dmin x ATR below the extreme.
Counting starts at a trend start B and needs a new extreme before the next pullback can count."""
import json, glob, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
def bars(m, rule):
    b = m.resample(rule, label='left', closed='left').agg(dict(open='first', high='max', low='min', close='last')).dropna()
    pc = b.close.shift(); tr = np.maximum(b.high - b.low, np.maximum((b.high - pc).abs(), (b.low - pc).abs())); b['atr'] = tr.rolling(14).mean()
    return b
def labels(dirname):
    D = pd.DataFrame([json.load(open(f)) for f in glob.glob(f'{S}/{dirname}/pbmarks/*.json')]); D['dt'] = pd.to_datetime(D.t, unit='s'); return D.sort_values('t')
def seq(D, tf):
    out = []; side = 0; n = 0; on = False; bt = None; legs = []
    for r in D[D.tf == tf].itertuples():
        if r.kind == 'B':
            if on: legs.append(n)
            side = r.side; n = 0; on = True; bt = r.t; out.append((r.t, 'B', side, 0, r.p, bt))
        elif r.kind == 'R':
            if on: legs.append(n)
            on = False; out.append((r.t, 'R', 0, 0, r.p, bt))
        elif on: n += 1; out.append((r.t, 'N', side, n, r.p, bt))
    if on: legs.append(n)
    return pd.DataFrame(out, columns=['t', 'k', 'side', 'n', 'p', 'bt']), legs
def count(b, T, bt, side, t_eval, par, dmin):
    i0 = np.searchsorted(T, bt); i1 = np.searchsorted(T, t_eval, 'right'); H = b.high.values; L = b.low.values; A = b.atr.values
    if i0 >= len(T): return 0
    n = 0; armed = True; ext = H[i0] if side == 1 else L[i0]
    for j in range(i0 + 1, min(i1, len(T))):
        newx = (H[j] > ext) if side == 1 else (L[j] < ext)
        if newx: ext = H[j] if side == 1 else L[j]
        k = j - par
        if k <= i0: continue
        w = L[max(i0, k - par):j + 1] if side == 1 else H[max(i0, k - par):j + 1]
        piv = (L[k] == w.min()) if side == 1 else (H[k] == w.max())
        deep = (ext - L[k] if side == 1 else H[k] - ext) >= dmin * A[k]
        if armed and piv and deep: n += 1; armed = False
        if not armed and newx: armed = True
    return n
