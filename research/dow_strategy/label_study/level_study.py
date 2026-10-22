"""(1) User's idea (2026-10-22): a trend extreme that stopped a running trend matters when the rebound from it reached
near the last protected level (戻り高値 in a downtrend) or beyond. At the FIRST return to that extreme, does price hold?
(2) H4 trend, a deep pullback back to the H4 protected level (押し安値): how often does it bounce?
Outcome at the touch bar: 'hold' = price moves 2 ATR(H4) away in the level's favour before an H4 close 0.5 ATR beyond it."""
import json, glob, sys, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
VD = {'EURUSD': 'stage_viewer', 'USDJPY': 'viewer_jpy', 'XAUUSD': 'viewer_XAUUSD', 'BTCUSD': 'viewer_BTCUSD', 'EURJPY': 'viewer_EURJPY', 'GBPUSD': 'viewer_GBPUSD'}
def load(pair):
    C = {}; PR = {}; PV = {}
    for f in sorted(glob.glob(f'{S}/{VD[pair]}/data/[12][0-9][0-9][0-9].json')):
        d = json.load(open(f))['H4']
        for c in d['candles']: C[c[0]] = c[1:5]
        for q in d['prot']: PR[q[0]] = (q[1], q[2])
        for p in d['piv']: PV[(p[0], p[1])] = p
    t = np.array(sorted(C)); a = np.array([C[x] for x in t], float)
    b = pd.DataFrame(a, columns=['o', 'h', 'l', 'c'], index=t); pc = b.c.shift()
    b['atr'] = np.maximum(b.h - b.l, np.maximum((b.h - pc).abs(), (b.l - pc).abs())).rolling(14).mean().bfill()
    b['pp'] = [PR.get(x, (None, None))[0] for x in t]; b['pd'] = [PR.get(x, (None, None))[1] for x in t]
    piv = sorted(PV.values()); return b, piv
def outcome(H, L, C, A, j, lvl, s, n=120):
    for k in range(j, min(len(H), j + n)):
        if (C[k] < lvl - 0.5 * A[j]) if s == 1 else (C[k] > lvl + 0.5 * A[j]): return 0
        if (H[k] >= lvl + 2 * A[j]) if s == 1 else (L[k] <= lvl - 2 * A[j]): return 1
    return np.nan
rows = []; rows2 = []
for pair in VD:
    b, piv = load(pair); T = b.index.values; H = b.h.values; L = b.l.values; C = b.c.values; A = b.atr.values; PP = b.pp.values; PD = b.pd.values
    yr = pd.to_datetime(T, unit='s').year; half = np.where(yr <= (2021 if pair == 'BTCUSD' else 2015), 1, 2)
    idx = {t: i for i, t in enumerate(T)}
    for p in piv:
        i = idx.get(p[0]); ci = idx.get(p[4])
        if i is None or ci is None: continue
        kind = p[1]; lvl = p[2]; s = 1 if kind == 'lo' else -1          # support (lo) / resistance (hi)
        trend = PD[i]; P = PP[i]
        if P is None or trend is None: continue
        if (kind == 'lo' and trend != 'down') or (kind == 'hi' and trend != 'up'): continue   # extreme of a running trend
        rng = (P - lvl) if s == 1 else (lvl - P)
        if not rng or rng <= 0: continue
        ext = lvl; touch = None
        for j in range(ci + 1, min(len(T), ci + 400)):
            ext = max(ext, H[j]) if s == 1 else min(ext, L[j])
            reb = (ext - lvl) * s
            if reb >= 2 * A[i] and ((L[j] <= lvl + 0.25 * A[i]) if s == 1 else (H[j] >= lvl - 0.25 * A[i])): touch = j; break
            if (C[j] < lvl - 0.5 * A[i]) if s == 1 else (C[j] > lvl + 0.5 * A[i]): break
        if touch is None: continue
        r = (ext - lvl) * s / rng
        rows.append((pair, half[touch], r, outcome(H, L, C, A, touch, lvl, s)))
    # (2) H4 trend, deep pullback to the protected level
    last = -999
    for j in range(20, len(T)):
        d = PD[j]; P = PP[j]
        if d not in ('up', 'down') or P is None: continue
        s = 1 if d == 'up' else -1
        if j - last < 12: continue
        if (L[j] <= P + 0.5 * A[j] and C[j] > P) if s == 1 else (H[j] >= P - 0.5 * A[j] and C[j] < P):
            last = j; rows2.append((pair, half[j], outcome(H, L, C, A, j + 1, P, s)))
R = pd.DataFrame(rows, columns=['pair', 'half', 'r', 'hold']).dropna()
R['rb'] = pd.cut(R.r, [0, 0.4, 0.8, 1.0, 9], labels=['戻り高値の4割未満', '4〜8割', '8割〜戻り高値', '戻り高値を超えた'])
print('### (1) トレンドを止めた高値・安値への「最初の戻り」で止まる割合（2ATR 反発が先 ÷ 0.5ATR 抜けが先）')
g = R.groupby(['rb', 'half'], observed=True).hold.agg(['mean', 'size']).unstack('half'); print(g.round(2).to_string())
print('\n通貨別（8割以上 vs 4割未満）'); R['big'] = R.r >= 0.8
print(R.groupby(['pair', 'big', 'half']).hold.mean().unstack(['big', 'half']).round(2).to_string())
R2 = pd.DataFrame(rows2, columns=['pair', 'half', 'hold']).dropna()
print('\n### (2) H4 トレンド中、押し安値（戻り高値）の 0.5ATR 以内まで深く戻った所で止まる割合')
print(R2.groupby(['pair', 'half']).hold.agg(['mean', 'size']).unstack('half').round(2).to_string())
