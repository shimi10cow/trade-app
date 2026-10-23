"""EURUSD: zone bounce only when the H4 trend is stretched (user, 2026-10-23). Features at each zone trade's entry:
  h4age  : H4 bars since the current H4 major trend began
  h4run  : move from the trend's start to its extreme so far, in ATR(H4)
  h4push : confirmed new swing highs (uptrend) / lows (downtrend) since the start = number of pushes
  dev4 / dev1 : distance of price from H4 / H1 SMA75 in ATR, signed so that + = stretched AGAINST the bounce
                (e.g. buying a bounce after a fall: price far below the MA is +)
  against : bounce direction is against the H4 trend (counter-trend) -> the case the idea is about
Trades: results/zone/Z_* (M15 engine, all patterns) and ZL_* (M5 engine, M15/M5 triggers). Choice on 2005-15, check 2016-26."""
import sys, glob, os
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
h4 = B.h4.reset_index(drop=True); C4 = pd.DatetimeIndex(B.C4); c4 = h4.c.to_numpy(float); A4 = atr(h4)
bars = B.R4['bars']; n = len(h4)
start = np.zeros(n, int); tr = [b[0] for b in bars]
for k in range(1, n): start[k] = start[k - 1] if tr[k] == tr[k - 1] else k
piv = sorted((e['available_idx'], e['kind'], e['price']) for e in B.R4['pivot_events'])
age = np.arange(n) - start; run = np.full(n, np.nan); push = np.zeros(n, int)
hi = h4.h.to_numpy(float); lo = h4.l.to_numpy(float)
pi = 0; cnt = 0; last_ext = None; cur_start = -1
for k in range(n):
    if start[k] != cur_start: cur_start = start[k]; cnt = 0; last_ext = None
    while pi < len(piv) and piv[pi][0] <= k:
        av, kind, pr = piv[pi]; pi += 1
        if tr[k] == 'up' and kind == 'hi' and (last_ext is None or pr > last_ext): cnt += 1; last_ext = pr
        if tr[k] == 'down' and kind == 'lo' and (last_ext is None or pr < last_ext): cnt += 1; last_ext = pr
    push[k] = cnt; s0 = start[k]
    if tr[k] == 'up': run[k] = (hi[s0:k + 1].max() - lo[s0]) / A4[k]
    elif tr[k] == 'down': run[k] = (hi[s0] - lo[s0:k + 1].min()) / A4[k]
ma4 = pd.Series(c4).rolling(75).mean().to_numpy()
h1 = B.h1.reset_index(drop=True); C1 = pd.DatetimeIndex(B.C1); c1 = h1.c.to_numpy(float); A1 = np.asarray(B.A1, float)
ma1 = pd.Series(c1).rolling(75).mean().to_numpy()
rows = []
for f in sorted(glob.glob(str(B.HERE / 'results' / 'zone' / 'Z*_*.csv'))):
    cfg = os.path.basename(f)[:-4]
    if cfg.startswith('Z5'): continue
    d = pd.read_csv(f)
    if not len(d): continue
    t = pd.to_datetime(d.setup_t if 'setup_t' in d else d.t)        # features when the setup was known
    k4 = np.clip(C4.searchsorted(t, 'right') - 1, 0, n - 1); k1 = np.clip(C1.searchsorted(t, 'right') - 1, 0, len(c1) - 1)
    s = d.side.to_numpy(); trk = np.array([tr[k] for k in k4])
    x = pd.DataFrame(dict(cfg=cfg, t=pd.to_datetime(d.t), R=d.R, side=s, h4age=age[k4], h4run=run[k4], h4push=push[k4],
                          dev4=-s * (c4[k4] - ma4[k4]) / A4[k4], dev1=-s * (c1[k1] - ma1[k1]) / A1[k1],
                          against=(trk == np.where(s == 1, 'down', 'up'))))
    rows.append(x)
X = pd.concat(rows, ignore_index=True); X['half'] = np.where(X.t.dt.year <= 2015, 1, 2)
X['pat'] = X.cfg.str.split('_').str[:3].str.join('_')
X.to_pickle(f"/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad/feat/zone_exhaust_{os.environ.get('M5_SYM', 'EURUSD')}.pkl")
pd.set_option('display.width', 220)
A = X[X.against]
print(f'H4 トレンドに逆らう跳ね返り（＝トレンドの止まり狙い）: {len(A)} 回（全設定の合計）、平均R 前半 {A[A.half==1].R.mean():+.3f} / 後半 {A[A.half==2].R.mean():+.3f}')
for c, bins in (('h4age', [0, 30, 60, 120, 9999]), ('h4run', [0, 3, 6, 10, 99]), ('h4push', [-1, 1, 2, 3, 99]), ('dev4', [-99, 0, 2, 4, 99]), ('dev1', [-99, 0, 2, 4, 99])):
    g = A.groupby([pd.cut(A[c], bins), 'half'], observed=True).R.agg(['count', 'mean']).unstack('half').round(3)
    print(f'\n-- {c}'); print(g.to_string())
