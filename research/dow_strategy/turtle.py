"""Daily breakout trend following (classic Donchian / turtle style) for trending commodities (oil) and as a check elsewhere.
D1 bars from broker M15. Entry at the D1 close beyond the highest high / lowest low of the last N days (20 / 55).
Stop k x ATR(D1, 20) (2 / 3). Exit at the D1 close beyond the opposite M-day extreme (10 / 20), or the stop.
Side: both, or long only ('buy'). One position at a time. Writes results/turtle/U_<N>_<M>_<k>_<side>.csv"""
import sys, os, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
OUT = B.HERE / 'results' / 'turtle'; OUT.mkdir(parents=True, exist_ok=True)
m = pd.DataFrame(dict(o=B.o, h=B.h, l=B.l, c=B.c), index=pd.DatetimeIndex(B.T15))
D = m.resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna(); D = D[D.index.dayofweek < 5] if os.environ.get('M5_SYM') != 'BTCUSD' else D   # BTC trades every day
pc = D.c.shift(); ATR = np.maximum(D.h - D.l, np.maximum((D.h - pc).abs(), (D.l - pc).abs())).rolling(20).mean()


def run(N_, M_, k, side):
    hiN = D.h.rolling(N_).max().shift(1); loN = D.l.rolling(N_).min().shift(1)
    hiM = D.h.rolling(M_).max().shift(1); loM = D.l.rolling(M_).min().shift(1)
    out = []; i = 0; n = len(D); idx = D.index; c = D.c.to_numpy(); hi = D.h.to_numpy(); lo = D.l.to_numpy(); op = D.o.to_numpy()
    while i < n - 1:
        s = 1 if c[i] > hiN.iloc[i] else -1 if (c[i] < loN.iloc[i] and side == 'both') else 0
        if idx[i] < B.START or s == 0 or not np.isfinite(ATR.iloc[i]): i += 1; continue
        en = c[i]; risk = k * ATR.iloc[i]; st = en - s * risk; xp = None
        for j in range(i + 1, n):
            if (lo[j] <= st) if s == 1 else (hi[j] >= st): xp = (min(st, op[j]) if s == 1 else max(st, op[j])); break
            if (c[j] < loM.iloc[j]) if s == 1 else (c[j] > hiM.iloc[j]): xp = c[j]; break
        if xp is None: xp = c[j]
        out.append(dict(t=idx[i] + pd.Timedelta('1D'), exit_t=idx[j] + pd.Timedelta('1D'), side=s, entry=en, risk=risk, exit=xp,
                        R=s * (xp - en) / risk - 2 * B.COST / risk))
        i = j + 1
    tr = pd.DataFrame(out)
    if len(tr): tr.to_csv(OUT / f'U_{N_}_{M_}_{k}_{side}.csv', index=False)
    return len(tr), round(tr.R.sum(), 1) if len(tr) else 0


if __name__ == '__main__':
    for cfg in itertools.product((20, 55), (10, 20), (2, 3), ('both', 'buy')):
        if cfg[1] >= cfg[0]: continue
        print(cfg, *run(*cfg), flush=True)
