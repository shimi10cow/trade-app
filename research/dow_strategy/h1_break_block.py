"""After an H1 trendline break, do we still buy? (user, 2026-10-23: once the H1 rising line breaks, new highs come less often
-> the question is whether to keep buying). Two user-style H1 lines from confirmed H1 swings (mirror for falling lines):
  'redraw' : through the last two confirmed higher lows (the user redraws from the 2nd to the 3rd point as the trend steepens)
  'outer'  : from the lowest low of the move (the impulse origin, lowest of the last 60 H1 bars) as the flattest line under all
             later lows (outer tangent)
Break = H1 close below the line, only if price had run >= 2 ATR(H1) above it (a real trend leg). After the break, entries in the
old direction are blocked until price trades above the pre-break high (trend resumed) or for at most 72h.
Run in a workspace; writes feat/h1blk_<SYM>.pkl (break events with the pre-break extreme)."""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SYM = os.environ.get('M5_SYM', 'EURUSD')
h1 = B.h1.reset_index(drop=True); C1 = pd.DatetimeIndex(B.C1); c = h1.c.to_numpy(float); hi = h1.h.to_numpy(float); lo = h1.l.to_numpy(float)
A = np.asarray(B.A1, float)
piv = sorted((e['available_idx'], e['idx'], e['kind'], e['price']) for e in B.R1['pivot_events'])
out = []
for mode in ('redraw', 'outer'):
    lows, highs = [], []; pi = 0; done = set()
    for i in range(60, len(h1)):
        while pi < len(piv) and piv[pi][0] <= i:
            av, ix, kind, pr = piv[pi]; pi += 1
            (lows if kind == 'lo' else highs).append((ix, pr))
        a = A[i] if np.isfinite(A[i]) and A[i] > 0 else np.nan
        for side, pts in ((1, lows), (-1, highs)):
            rec = [p for p in pts if p[0] >= i - 60]
            if len(rec) < 2: continue
            if mode == 'redraw':
                (i1, p1), (i2, p2) = rec[-2], rec[-1]
                if (side == 1 and p2 <= p1) or (side == -1 and p2 >= p1): continue
                sl = (p2 - p1) / (i2 - i1)
            else:
                k0 = int(np.argmin([p for _, p in rec])) if side == 1 else int(np.argmax([p for _, p in rec]))
                i1, p1 = rec[k0]; later = rec[k0 + 1:]
                if not later: continue
                sls = [(p - p1) / (ix - i1) for ix, p in later]
                sl = min(sls) if side == 1 else max(sls)
                if side * sl <= 0: continue
                i2 = later[-1][0]
            key = (mode, side, i1, round(sl, 10))
            if key in done: continue
            v = p1 + sl * (i - i1)
            if (side == 1 and c[i] < v) or (side == -1 and c[i] > v):
                done.add(key)
                seg = np.arange(i1, i); run = (side * ((hi[seg] if side == 1 else lo[seg]) - (p1 + sl * (seg - i1)))).max() / a
                if run >= 2:
                    ext = hi[i1:i + 1].max() if side == 1 else lo[i1:i + 1].min()
                    # is the outer (flatter) line from the move's origin still intact at this bar? (user: if the 1-2 line
                    # still holds, a break of the steeper 2-3 line often resumes)
                    k0 = int(np.argmin([p for _, p in rec])) if side == 1 else int(np.argmax([p for _, p in rec]))
                    io, po = rec[k0]; lat = rec[k0 + 1:]
                    outer_ok = None
                    if lat:
                        so = [(p - po) / (ix - io) for ix, p in lat]; so = min(so) if side == 1 else max(so)
                        vo = po + so * (i - io); outer_ok = bool((c[i] >= vo) if side == 1 else (c[i] <= vo))
                        if abs(so - sl) < 1e-12: outer_ok = None          # the steep line IS the outer line
                    out.append(dict(mode=mode, t=C1[i], side=side, ext=ext, slope=abs(sl) / a, run=run, outer_ok=outer_ok))
D = pd.DataFrame(out).drop_duplicates(['mode', 't', 'side'])
# when is the old extreme regained (H1 close-time index)
ends = []
for x in D.itertuples():
    i = C1.searchsorted(x.t); j = i + 1; lim = min(len(c), i + 73)
    while j < lim and not ((hi[j] > x.ext) if x.side == 1 else (lo[j] < x.ext)): j += 1
    ends.append(C1[min(j, len(c) - 1)])
D['until'] = ends
D.to_pickle(f'{S}/feat/h1blk_{SYM}.pkl'); print(SYM, D.groupby('mode').size().to_dict())
