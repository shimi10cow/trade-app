"""M15 correction lines (user rules, 2026-10-20, after judging 51 M15 auto lines).

User: on M15 a trendline is drawn only for a CORRECTION of the higher trend. In an H1 uptrend, the M15 correction
shows lower highs (sellers coming in) while the H1 protected low holds; connect those clear peaks with a down line.
Its break = end of the correction. Not wanted: lines in the impulse direction, peaks that are not clear,
an extremely steep line, a start placed far back on the trend (too shallow), and near-flat lines (double top).
A flat line is fine only as part of a triangle (not handled here).

Rule (uptrend; mirror for downtrend):
  context : a correction of the preceding M15 impulse - A tops a rise of >= IMP x ATR(M15) from the lowest low of the
            last IMPW bars (the origin; the user's 'long-term protected low'). Judged lines: impulse >= 6 ATR for 95 %
            of the accepted lines vs 56 % of the 'not needed' ones; engine H1/H4/D1 trend did not separate them
  A       : a confirmed M15 swing high that is the highest high of the previous LOOK bars (start of the correction)
  B       : a later confirmed M15 swing high, lower than A by >= DROP x ATR(M15), with a clear trough between
            (B - lowest low between A and B >= PROM x ATR); peaks between A and B at A's height (double top) are skipped
            a new high above A cancels A
  line    : through A and B; a later confirmed lower high above the line makes it the outer tangent (user style)
  span    : A to B within MAXAB bars (a start far back makes the line too shallow)
  ends    : close above the line (broken = correction over), close below the impulse origin (invalid), MAXLEN bars
Output per line: [a_t, a_p, b_t, b_p, created_t, end_t, kind('hi' = down line over highs), broken, ll, h4_with]
  ll = the correction already made a lower low (lowest low between A and creation < the swing low before A)
Usage: DT_START=2005-01-01 DT_CACHE=... python dow_strategy/m15_corr_lines.py <out_dir> <years...>"""
import bisect, json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402

LOOK, DROP, PROM, MAXAB, MAXLEN, IMPW, IMP = 40, 0.6, 1.5, 40, 300, 96, 6.0
H, L, C = B.h, B.l, B.c
A15 = atr(B.m15)
T = B.T15; CL15 = list(T + pd.Timedelta(minutes=15))


def lines():
    last = {}
    for e in B.R15['pivot_events']:
        last[e['id']] = e
    piv = sorted((e['idx'], e['kind'], e['price'], e['available_idx']) for e in last.values())
    byk = {k: [p for p in piv if p[1] == k] for k in ('hi', 'lo')}
    byk_i = {k: [p[0] for p in v] for k, v in byk.items()}
    n = len(T); out = []
    for ia, kind, pa, avail in piv:
        hi = kind == 'hi'; s = -1 if hi else 1             # s = direction of the line
        j0 = max(0, ia - LOOK)
        if (hi and H[j0:ia].size and H[j0:ia].max() > pa) or ((not hi) and L[j0:ia].size and L[j0:ia].min() < pa):
            continue
        a = A15[ia]
        if not np.isfinite(a) or a <= 0 or ia < IMPW:
            continue
        # correction of the preceding M15 impulse: A tops a move of >= IMP x ATR over the last IMPW bars
        origin = L[ia - IMPW:ia + 1].min() if hi else H[ia - IMPW:ia + 1].max()
        if (pa - origin if hi else origin - pa) < IMP * a:
            continue
        lo_, hi_ = bisect.bisect_right(byk_i[kind], ia), bisect.bisect_right(byk_i[kind], ia + MAXLEN)
        later = sorted(byk[kind][lo_:hi_], key=lambda p: p[3])
        ok_ = 'lo' if hi else 'hi'; jo = bisect.bisect_left(byk_i[ok_], ia) - 1
        before = byk[ok_][jo][2] if jo >= 0 else None       # swing low before A (for the lower-low flag)
        b = slope = created = None; q = 0; end = None; broken = False
        for j in range(ia + 1, min(n, ia + MAXLEN)):
            while q < len(later) and later[q][3] <= j:
                pb = later[q]; q += 1
                if b is None:
                    if pb[0] - ia > MAXAB:
                        continue
                    if s * (pb[2] - pa) < DROP * a:         # not lower enough than A (double top): skip
                        continue
                    seg = L[ia:pb[0] + 1] if hi else H[ia:pb[0] + 1]
                    trough = seg.min() if hi else seg.max()
                    if (pb[2] - trough if hi else trough - pb[2]) < PROM * a:
                        continue                               # peaks not clear
                    b, slope, created = pb, (pb[2] - pa) / (pb[0] - ia), j
                else:
                    sl = (pb[2] - pa) / (pb[0] - ia)
                    if (sl > slope) if hi else (sl < slope):
                        slope, b = sl, pb                      # outer tangent over later lower highs
            if (H[j] > pa) if hi else (L[j] < pa):
                end = j; break                                  # new extreme beyond A: no correction line
            if (C[j] < origin) if hi else (C[j] > origin):
                end = j; break                                  # impulse origin broken: not a correction any more
            if slope is not None:
                v = pa + slope * (j - ia)
                if (C[j] > v) if hi else (C[j] < v):
                    end, broken = j, True; break
        if b is None:
            continue
        seg = L[ia:created + 1] if hi else H[ia:created + 1]
        ll = bool(before is not None and ((seg.min() < before) if hi else (seg.max() > before)))
        k4 = bisect.bisect_right(B.C4, CL15[created]) - 1
        h4w = B.R4['bars'][k4][0] == ('up' if hi else 'down') if k4 >= 0 else False
        out.append((ia, pa, b[0], b[2], created, end, kind, broken, ll, h4w))
    return out


if __name__ == '__main__':
    outd = Path(sys.argv[1]); years = [int(y) for y in sys.argv[2:]]
    sec = lambda i: int((T[i] - pd.Timestamp('1970-01-01')) // pd.Timedelta(seconds=1))
    LS = lines()
    print('lines', len(LS), 'broken', sum(x[7] for x in LS))
    for y in years:
        rows = [[sec(ia), round(pa, 5), sec(ib), round(pb, 5), sec(cr), sec(en) if en is not None else None, kind, bool(br), ll, h4w]
                for ia, pa, ib, pb, cr, en, kind, br, ll, h4w in LS if T[cr].year == y]
        (outd / f'cl_{y}.json').write_text(json.dumps(rows, separators=(',', ':')), encoding='utf-8')
        print(y, len(rows))
