"""Opening-range breakout for indices (2026-10-23). Cash open: US indices 09:30 New York, JP225 09:00 Tokyo, from broker
M15 bars (time zones converted properly). Range = first 30 or 60 min. Breakout = first later bar (within 6h) trading beyond
the range high (buy) / low (sell) -> entry at the range edge (stop order), one trade a day.
Side: 'both' or 'trend' (only in the direction of D1 close vs a rising/falling D1 SMA50). Stop: other side of the range ('far')
or its middle ('mid'). Exit: 1R / 2R target, or the close of the 6h window ('eod'). Writes results/orb/O_<...>.csv"""
import sys, os, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
OUT = B.HERE / 'results' / 'orb'; OUT.mkdir(parents=True, exist_ok=True)
SYM = os.environ.get('M5_SYM', 'US30')
TZ, OPEN = ('Asia/Tokyo', (9, 0)) if SYM == 'JP225' else ('America/New_York', (9, 30))
T = pd.DatetimeIndex(B.T15); o, h, l, c = B.o, B.h, B.l, B.c
loc = T.tz_localize('Europe/Athens', ambiguous='NaT', nonexistent='NaT').tz_convert(TZ)
day = pd.Series(loc.date, index=range(len(T))); mins = loc.hour * 60 + loc.minute
op = OPEN[0] * 60 + OPEN[1]
d1 = pd.Series(c, index=T).resample('1D').last().dropna(); ma = d1.rolling(50).mean()
up = ((d1 > ma) & (ma > ma.shift(5))); dn = ((d1 < ma) & (ma < ma.shift(5))); up.index = up.index + pd.Timedelta('1D'); dn.index = dn.index + pd.Timedelta('1D')


def run(orm, side, stop, ex):
    out = []
    starts = np.nonzero((mins == op) & (T >= B.START))[0]
    for s0 in starts:
        n_or = orm // 15; s1 = s0 + n_or
        if s1 + 1 >= len(T) or (T[s1] - T[s0]) > pd.Timedelta(minutes=orm + 1): continue
        rh, rl = h[s0:s1].max(), l[s0:s1].min(); rg = rh - rl
        if rg <= 0: continue
        i = up.index.searchsorted(T[s0], 'right') - 1; tu = bool(up.iloc[i]) if i >= 0 else False; td = bool(dn.iloc[i]) if i >= 0 else False
        end = min(s1 + 24, len(T) - 1)
        for k in range(s1, end):
            sd = 1 if h[k] > rh else -1 if l[k] < rl else 0
            if sd == 0: continue
            if h[k] > rh and l[k] < rl: break                        # both sides in one bar: skip the day
            if side == 'trend' and not ((sd == 1 and tu) or (sd == -1 and td)): break
            en = rh if sd == 1 else rl; st = (rl if sd == 1 else rh) if stop == 'far' else (rh + rl) / 2
            risk = sd * (en - st); tp = {'tp1': 1, 'tp2': 2}.get(ex)
            xp, xk = c[end], end
            for m in range(k, end + 1):
                if (l[m] <= st) if sd == 1 else (h[m] >= st): xp, xk = st, m; break
                if tp and ((h[m] >= en + tp * risk) if sd == 1 else (l[m] <= en - tp * risk)): xp, xk = en + sd * tp * risk, m; break
            out.append(dict(t=T[k], exit_t=T[xk], side=sd, entry=en, risk=risk, exit=xp, R=sd * (xp - en) / risk - B.COST / risk))
            break
    tr = pd.DataFrame(out)
    if len(tr): tr.to_csv(OUT / f'O_{orm}_{side}_{stop}_{ex}.csv', index=False)
    return len(tr), round(tr.R.sum(), 1) if len(tr) else 0


if __name__ == '__main__':
    for c_ in itertools.product((30, 60), ('both', 'trend'), ('far', 'mid'), ('tp1', 'tp2', 'eod')):
        print(c_, *run(*c_), flush=True)
