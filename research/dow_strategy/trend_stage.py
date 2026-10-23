"""Trend stage on H4 and H1 at every bar close (for 'late in the trend: still follow?', user 2026-10-23).
For each timeframe (major Dow trend from dow_trend bars):
  trend : 'up' / 'down' / other
  age   : bars since the current major trend began
  run   : move from the trend's start to its extreme so far, in ATR of that timeframe
  push  : confirmed new swing highs (up) / lows (down) since the start = number of pushes (trend legs)
  dev   : distance of the close from SMA75 in ATR, + = in the trend direction (stretched)
Run in a workspace; writes feat/stage_<SYM>.pkl = {'H4': DataFrame(t=close time, ...), 'H1': ...}"""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SYM = os.environ.get('M5_SYM', 'EURUSD')


def stage(df, R, close):
    df = df.reset_index(drop=True); n = len(df); A = np.asarray(atr(df), float)
    c, hi, lo = (df[z].to_numpy(float) for z in 'chl')
    tr = [b[0] for b in R['bars']]; start = np.zeros(n, int)
    for k in range(1, n): start[k] = start[k - 1] if tr[k] == tr[k - 1] else k
    piv = sorted((e['available_idx'], e['kind'], e['price']) for e in R['pivot_events'])
    run = np.full(n, np.nan); push = np.zeros(n, int); pi = 0; cnt = 0; last = None; cur = -1
    for k in range(n):
        if start[k] != cur: cur = start[k]; cnt = 0; last = None
        while pi < len(piv) and piv[pi][0] <= k:
            av, kind, pr = piv[pi]; pi += 1
            if tr[k] == 'up' and kind == 'hi' and (last is None or pr > last): cnt += 1; last = pr
            if tr[k] == 'down' and kind == 'lo' and (last is None or pr < last): cnt += 1; last = pr
        push[k] = cnt; s0 = start[k]
        if tr[k] == 'up': run[k] = (hi[s0:k + 1].max() - lo[s0]) / A[k]
        elif tr[k] == 'down': run[k] = (hi[s0] - lo[s0:k + 1].min()) / A[k]
    ma = pd.Series(c).rolling(75).mean().to_numpy(); sg = np.array([1 if x == 'up' else -1 if x == 'down' else 0 for x in tr])
    return pd.DataFrame(dict(t=pd.DatetimeIndex(close), trend=sg, age=np.arange(n) - start, run=run, push=push, dev=sg * (c - ma) / A))


out = {'H4': stage(B.h4, B.R4, B.C4), 'H1': stage(B.h1, B.R1, B.C1)}
pd.to_pickle(out, f'{S}/feat/stage_{SYM}.pkl'); print(SYM, {k: len(v) for k, v in out.items()})
