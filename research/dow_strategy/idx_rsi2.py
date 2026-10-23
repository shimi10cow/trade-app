"""Daily short-term mean reversion in an uptrend (index character: upward drift + short-term pullbacks that come back).
D1 bars from broker M15 (day = broker date). Long only.
Entry at the D1 close when: close > SMA(trend) and RSI(2) < lo   (trend: 100 / 200 days; lo: 5 / 10 / 20)
Exit at the D1 close when: close > SMA5 ('ma5'), or RSI(2) > 70 ('rsi70'), or after 5 days ('d5').
Stop: none, or 2.5 x ATR(D1, 14) below entry ('st'). R = move / (2.5 x ATR) for comparability. Writes results/rsi2/M_<...>.csv"""
import sys, os, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
OUT = B.HERE / 'results' / 'rsi2'; OUT.mkdir(parents=True, exist_ok=True)
m = pd.DataFrame(dict(o=B.o, h=B.h, l=B.l, c=B.c), index=pd.DatetimeIndex(B.T15))
D = m.resample('1D').agg(dict(o='first', h='max', l='min', c='last')).dropna()
D = D[D.index.dayofweek < 5]
c = D.c; dlt = c.diff(); up = dlt.clip(lower=0).ewm(alpha=1 / 2).mean(); dn = (-dlt.clip(upper=0)).ewm(alpha=1 / 2).mean()
rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
pc = c.shift(); atr = np.maximum(D.h - D.l, np.maximum((D.h - pc).abs(), (D.l - pc).abs())).rolling(14).mean()
ma5 = c.rolling(5).mean(); MA = {n: c.rolling(n).mean() for n in (100, 200)}


def run(tr, lo, ex, st):
    out = []; i = 0; idx = D.index; n = len(D)
    while i < n - 1:
        if idx[i] < B.START or not (c.iloc[i] > MA[tr].iloc[i] and rsi.iloc[i] < lo and np.isfinite(atr.iloc[i])):
            i += 1; continue
        en = c.iloc[i]; risk = 2.5 * atr.iloc[i]; stp = en - risk; xp = None
        for j in range(i + 1, min(i + 30, n)):
            if st == 'st' and D.l.iloc[j] <= stp: xp = min(stp, D.o.iloc[j]); break
            done = (c.iloc[j] > ma5.iloc[j]) if ex == 'ma5' else (rsi.iloc[j] > 70) if ex == 'rsi70' else (j - i >= 5)
            if done: xp = c.iloc[j]; break
        if xp is None: xp = c.iloc[j]
        out.append(dict(t=idx[i] + pd.Timedelta('1D'), exit_t=idx[j] + pd.Timedelta('1D'), side=1, entry=en, risk=risk, exit=xp,
                        R=(xp - en) / risk - 2 * B.COST / risk))
        i = j + 1
    tr_ = pd.DataFrame(out)
    if len(tr_): tr_.to_csv(OUT / f'M_{tr}_{lo}_{ex}_{st}.csv', index=False)
    return len(tr_), round(tr_.R.sum(), 1) if len(tr_) else 0


if __name__ == '__main__':
    for cfg in itertools.product((100, 200), (5, 10, 20), ('ma5', 'rsi70', 'd5'), ('none', 'st')):
        print(cfg, *run(*cfg), flush=True)
