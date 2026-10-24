"""M15 trend line break, then H1 (user, 2026-10-23: lines can be drawn on the M15 impulse too; at the end of a trend the
M15 line breaks first, then the H1 line. Right after the M15 break: be careful for a while (not a long block)).
M15 impulse line = through the last two confirmed M15 higher lows (lower highs for a down trend), known at the M15 close.
Break = M15 close beyond the line after price ran >= 1.5 ATR(M15) away from it. For each break we record:
  h1   : state of the H1 impulse line at that moment (h1_break_block.py 'redraw' events): 'H1も割れ済' if an H1 break of
         the same side happened in the last 72h and the old extreme was not regained yet, else 'H1は健在'
  mv12 / mv48 : move over the next 12 / 48 M15 bars in the break direction (ATR M15); regain48 : old extreme regained
  kind : '推進' if the H1 Dow (last two H1 swings) runs the same way as the M15 line, '調整' if against, else 混在
  h1next : the H1 line breaks within the next 16h (the M15 -> H1 sequence)
Run in a workspace after h1_break_block.py; writes feat/m15brk_<SYM>.pkl."""
import os, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
SYM = os.environ.get('M5_SYM', 'EURUSD')
m = B.m15.reset_index(drop=True); CL = pd.DatetimeIndex(pd.to_datetime(m.t) + TF_LEN['M15'])
c, hi, lo = (m[z].to_numpy(float) for z in 'chl'); A = np.asarray(atr(m), float)
piv = sorted((e['available_idx'], e['idx'], e['kind'], e['price']) for e in B.R15['pivot_events'])
H1P = B.H1P; H1PT = pd.DatetimeIndex(B.H1PT)


def h1dow(t):
    k = H1PT.searchsorted(t, 'right'); hs = [p for _, kd, p in H1P[max(0, k - 12):k] if kd == 'hi'][-2:]; ls = [p for _, kd, p in H1P[max(0, k - 12):k] if kd == 'lo'][-2:]
    if len(hs) < 2 or len(ls) < 2: return 0
    return 1 if (hs[1] > hs[0] and ls[1] > ls[0]) else (-1 if (hs[1] < hs[0] and ls[1] < ls[0]) else 0)


H = pd.read_pickle(f'{S}/feat/h1blk_{SYM}.pkl'); H = H[H['mode'] == 'redraw']
out = []; lows, highs = [], []; pi = 0; done = set()
for i in range(len(m)):
    while pi < len(piv) and piv[pi][0] <= i:
        av, ix, kind, pr = piv[pi]; pi += 1
        (lows if kind == 'lo' else highs).append((ix, pr))
    for side, pts in ((1, lows), (-1, highs)):
        if len(pts) < 2: continue
        (i1, p1), (i2, p2) = pts[-2], pts[-1]
        if (side == 1 and p2 <= p1) or (side == -1 and p2 >= p1) or (side, i1, i2) in done: continue
        sl = (p2 - p1) / (i2 - i1); v = p2 + sl * (i - i2)
        if (side == 1 and c[i] < v) or (side == -1 and c[i] > v):
            done.add((side, i1, i2)); a = A[i] if np.isfinite(A[i]) and A[i] > 0 else np.nan
            seg = np.arange(i1, i); run = (side * ((hi[seg] if side == 1 else lo[seg]) - (p1 + sl * (seg - i1)))).max() / a
            if run < 1.5 or i - i1 < 8: continue
            ext = hi[i1:i + 1].max() if side == 1 else lo[i1:i + 1].min()
            j12, j48 = min(i + 12, len(c) - 1), min(i + 48, len(c) - 1)
            fut = (hi[i + 1:i + 49] > ext) if side == 1 else (lo[i + 1:i + 49] < ext)
            t = CL[i]; hs = H[H.side == side]
            prev = hs[(hs.t <= t) & (hs.t > t - pd.Timedelta('72h')) & (hs.until > t)]
            nxt = hs[(hs.t > t) & (hs.t <= t + pd.Timedelta('16h'))]
            reg = np.nonzero(fut)[0]
            out.append(dict(t=t, side=side, ext=ext, slope=abs(sl) / a, run=run,
                            h1='H1も割れ済' if len(prev) else 'H1は健在', h1next=len(nxt) > 0, kind={1: '推進', -1: '調整', 0: '混在'}[h1dow(t) * side],
                            mv12=-side * (c[j12] - c[i]) / a, mv48=-side * (c[j48] - c[i]) / a, regain48=bool(fut.any()),
                            until=CL[min(i + 1 + reg[0], len(c) - 1)] if len(reg) else CL[min(i + 48, len(c) - 1)]))
D = pd.DataFrame(out); D.to_pickle(f'{S}/feat/m15brk_{SYM}.pkl')
pd.set_option('display.width', 200)
D['half'] = np.where(D.t.dt.year <= {'EURUSD': 2015, 'USDJPY': 2015, 'XAUUSD': 2015, 'XAGUSD': 2015, 'US30': 2020}.get(SYM, 2021), 1, 2)
print(SYM, len(D), 'breaks')
print(D.groupby(['kind', 'h1', 'half']).agg(n=('t', 'size'), mv12=('mv12', 'mean'), mv48=('mv48', 'mean'), regain=('regain48', 'mean'), h1next=('h1next', 'mean')).round(2).to_string())
