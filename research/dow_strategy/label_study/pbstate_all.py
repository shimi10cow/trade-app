"""For every bar of H1 / H4 on every instrument: trend direction (major Dow, from the viewer data) and the swing-based
pullback count since the trend started (pbcount rule fitted to the user's labels). Then attach to every EA trade."""
import json, glob, sys, numpy as np, pandas as pd
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
VD = {'EURUSD': 'stage_viewer', 'USDJPY': 'viewer_jpy', 'XAUUSD': 'viewer_XAUUSD', 'BTCUSD': 'viewer_BTCUSD', 'EURJPY': 'viewer_EURJPY', 'GBPUSD': 'viewer_GBPUSD'}
PAR = {'H1': (3, 1.0), 'H4': (2, 1.5)}
def load(pair):
    C = {'H1': {}, 'H4': {}}; P = {'H1': {}, 'H4': {}}
    for f in sorted(glob.glob(f'{S}/{VD[pair]}/data/[12][0-9][0-9][0-9].json')):
        d = json.load(open(f))
        for tf in ('H1', 'H4'):
            for c in d[tf]['candles']: C[tf][c[0]] = c[1:5]
            for q in d[tf]['prot']: P[tf][q[0]] = q[2]
    out = {}
    for tf in ('H1', 'H4'):
        t = np.array(sorted(C[tf])); a = np.array([C[tf][x] for x in t], float)
        b = pd.DataFrame(a, columns=['open', 'high', 'low', 'close'], index=t)
        pc = b.close.shift(); tr = np.maximum(b.high - b.low, np.maximum((b.high - pc).abs(), (b.low - pc).abs())); b['atr'] = tr.rolling(14).mean().bfill()
        b['dir'] = [1 if P[tf].get(x) == 'up' else -1 if P[tf].get(x) == 'down' else 0 for x in t]
        out[tf] = b
    return out
def states(b, par, dmin):
    """per bar (known at its close): trend dir, pullback count since the trend started, bars since start, in-pullback flag"""
    H = b.high.values; L = b.low.values; A = b.atr.values; Dd = b.dir.values; n = len(b)
    cnt = np.zeros(n, int); since = np.zeros(n, int); inpb = np.zeros(n, bool)
    i0 = 0; side = 0; ext = 0; armed = True; c = 0
    for j in range(n):
        if Dd[j] != side:
            side = Dd[j]; i0 = j; c = 0; armed = True; ext = H[j] if side == 1 else L[j]
        elif side:
            newx = (H[j] > ext) if side == 1 else (L[j] < ext)
            if newx: ext = H[j] if side == 1 else L[j]
            k = j - par
            if k > i0:
                w = L[max(i0, k - par):j + 1] if side == 1 else H[max(i0, k - par):j + 1]
                piv = (L[k] == w.min()) if side == 1 else (H[k] == w.max())
                deep = (ext - L[k] if side == 1 else H[k] - ext) >= dmin * A[k]
                if armed and piv and deep: c += 1; armed = False
            if not armed and newx: armed = True
        cnt[j] = c; since[j] = j - i0; inpb[j] = not armed
    return pd.DataFrame(dict(dir=Dd, cnt=cnt, since=since, inpb=inpb), index=b.index)
if __name__ == '__main__':
    pair = sys.argv[1]; B = load(pair); res = {}
    for tf in ('H1', 'H4'):
        st = states(B[tf], *PAR[tf]); st.to_pickle(f'{S}/feat/pbstate_{pair}_{tf}.pkl'); res[tf] = st
    T = pd.read_pickle(f'{S}/feat/all_trades_hold.pkl'); T = T[T.pair == pair]
    try:
        Q = pd.read_pickle(f'{S}/feat/q_best.pkl'); Q = Q[Q.pair == pair]
        if len(Q): Q = Q.assign(ea='Q', side=np.nan, half=np.where(Q.tt.dt.year <= (2021 if pair == 'BTCUSD' else 2015), 1, 2))
    except Exception: Q = None
    out = []
    for tf in ('H1', 'H4'):
        st = res[tf]; L = 3600 if tf == 'H1' else 14400; tt = np.array([int(x.timestamp()) for x in T.tt])
        k = np.searchsorted(st.index.values + L, tt, 'right') - 1
        ok = k >= 0; s = st.iloc[np.maximum(k, 0)]
        T[f'{tf}_dir'] = np.where(ok, s.dir.values * T.side.values, 0); T[f'{tf}_cnt'] = s.cnt.values; T[f'{tf}_inpb'] = s.inpb.values; T[f'{tf}_since'] = s.since.values
    T.to_pickle(f'{S}/feat/pbstate_trades_{pair}.pkl'); print(pair, len(T), 'trades', {tf: len(res[tf]) for tf in res})
