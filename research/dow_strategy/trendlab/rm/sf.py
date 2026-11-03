"""User idea (2026-11-03): H1 SMA20/75 cross = the H1 turn, pick the pullback with the M15 stochastic (= the original stochastic EA's
trades, stoch/tr_{sym}.pkl), and judge by: the prior trend (H1 bars / size of the previous opposite MA regime), the retracement of
the turning wave (38.2 / 50 / 61.8), and whether the pullback low sits on a broken H1 swing (old high for buys = the exit/entry door).
Exits re-simulated in the live Frames space: H1 = trail confirmed H1 swings from +1R (P's exit), M2 = M15 swings from +2R; orig = the EA's own R.
"""
import sys, pickle, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app'); sys.path.insert(0, '/home/user/trade-app/research')
sym = sys.argv[1]; TL_ = '/home/user/trendlab'
COST = {'GBPUSD': 1.5e-4, 'AUDUSD': 1.3e-4, 'USDCAD': 2e-4, 'USDCHF': 2e-4, 'EURJPY': 2e-4, 'AUDJPY': 2.5e-4, 'CADJPY': 3e-4, 'CHFJPY': 3e-4,
        'EURUSD': 1.2e-4, 'USDJPY': 1.5e-4, 'XAUUSD': 2.5e-4}[sym]
F = pickle.load(open(f'{TL_}/live_frames_{sym}.pkl', 'rb'))
T = F.T15.to_numpy(); o, h, l, c = F.o, F.h, F.l, F.c; n = len(c); CL = T + np.timedelta64(15, 'm')
H = F.h1; C1 = np.array(F.C1, dtype='datetime64[ns]'); A1 = F.A1
hh, ll, cc = H.h.to_numpy(), H.l.to_numpy(), H.c.to_numpy()
m20 = pd.Series(cc).rolling(20).mean().to_numpy(); m75 = pd.Series(cc).rolling(75).mean().to_numpy()
sg = np.sign(m20 - m75); sg[~np.isfinite(sg)] = 0
chg = np.flatnonzero(np.r_[False, sg[1:] != sg[:-1]])          # H1 bar index where a new regime starts
def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
H1P, P15 = arr(F.H1P), arr(F.P15)
HP_anchor = {}   # confirmed H1 swings with their price; anchor time unknown here -> use confirm time
def sim(e, s, en, sl, piv, start, tp=None):
    risk = (en - sl) * s; on = False
    for j in range(e, min(e + 96 * 20, n)):
        if (l[j] <= sl) if s == 1 else (h[j] >= sl): return ((min(sl, o[j]) if s == 1 else max(sl, o[j])) - en) * s / risk, j
        if tp is not None and ((h[j] >= tp) if s == 1 else (l[j] <= tp)): return (tp - en) * s / risk, j
        if piv is None: continue
        if ((h[j] - en) if s == 1 else (en - l[j])) / risk >= start: on = True
        if on:
            TT, KK, PV = piv; q = np.searchsorted(TT, CL[j], side='right') - 1; want = 'lo' if s == 1 else 'hi'
            while q >= 0 and KK[q] != want: q -= 1
            if q >= 0 and (PV[q] - sl) * s > 0 and (PV[q] - c[j]) * s < 0: sl = PV[q]
    j = min(e + 96 * 20, n) - 1; return (c[j] - en) * s / risk, j
tr = pd.read_pickle(f'{TL_}/stoch/tr_{sym}.pkl'); k = 100.0 if sym.endswith('JPY') else 1.0
rows = []
for r in tr.itertuples():
    s = int(r.side); ts = np.datetime64(pd.Timestamp(r.time)); i = int(np.searchsorted(T, ts))
    if i >= n - 1 or T[i] != ts: continue
    en = r.entry / k; sl = r.initial_sl / k
    if (en - sl) * s <= 0: continue
    k1 = int(np.searchsorted(C1, CL[i], side='right')) - 1            # last closed H1 bar
    if k1 < 200: continue
    q = np.searchsorted(chg, k1, side='right') - 1
    if q < 2 or sg[k1] != s: continue
    st, pst = chg[q], chg[q - 1]                                        # this regime start, previous regime start
    a1 = A1[k1]; age = k1 - st; pre_len = st - pst
    seg = slice(pst, st)
    pre_size = (hh[seg].max() - ll[seg].min()) / a1
    # turning wave: extreme X (lowest low for buys) from the previous regime start to now, then the wave top since X, then the pullback
    w0 = pst; xs = (ll if s == 1 else hh)[w0:k1 + 1]; xi = w0 + (int(np.argmin(xs)) if s == 1 else int(np.argmax(xs)))
    X = ll[xi] if s == 1 else hh[xi]
    i_x = int(np.searchsorted(T, np.datetime64(C1[xi]) - np.timedelta64(1, 'h')))
    seg15 = slice(i_x, i + 1)
    top_rel = int(np.argmax(h[seg15])) if s == 1 else int(np.argmin(l[seg15])); ti = i_x + top_rel
    TOP = h[ti] if s == 1 else l[ti]
    PB = (l[ti:i + 1].min() if s == 1 else h[ti:i + 1].max())
    wave = (TOP - X) * s
    retr = (TOP - PB) * s / wave if wave > 0 else np.nan
    # door: a confirmed H1 swing high (low for sells) confirmed before the wave top, price between X and TOP, that the wave broke
    TT, KK, PV = H1P; qa = np.searchsorted(TT, np.datetime64(C1[xi]) - np.timedelta64(30, 'D')); qb = np.searchsorted(TT, T[ti], side='right')
    want = 'hi' if s == 1 else 'lo'
    doors = [PV[j] for j in range(qa, qb) if KK[j] == want and (PV[j] - X) * s > 0 and (TOP - PV[j]) * s > 0]
    door = min((abs(PB - p) / a1 for p in doors), default=np.nan)
    sl75 = (m75[k1] - m75[k1 - 10]) * s / a1
    res = dict(orig=r.R)
    for nm, (piv, stt, tp) in (('H1', (H1P, 1, None)), ('M2', (P15, 2, None)), ('M1', (P15, 1, None)), ('TOP', (None, 0, TOP if (TOP - en) * s > 0 else None))):
        if nm == 'TOP' and tp is None: res[nm] = np.nan; continue
        R, j = sim(i + 1, s, en, sl, piv, stt, tp); res[nm] = R - COST / (en - sl) / s
    res['topR'] = (TOP - en) * s / ((en - sl) * s)
    rows.append(dict(sym=sym, t=pd.Timestamp(r.time), side=s, point=r.point, age=age, pre_len=pre_len, pre_size=pre_size, wave=wave / a1,
                     retr=retr, door=door, sl75=sl75, riskA=(en - sl) * s / a1, **res))
pd.DataFrame(rows).to_pickle(f'{TL_}/rm/sf_{sym}.pkl'); print(sym, len(tr), len(rows), flush=True)
