"""User hypothesis: trades that reach +1R and come back often ran into resistance ahead.
Levels = H4 / H1 swing highs AND lows confirmed before entry (last 60 H4 / 120 H1 swings), lying beyond entry in the trade direction.
  near_lvl  : distance (R) from entry to the first such level beyond +1R ... measured as the first level in (1R, 4R]
  peak_at   : the trade's best price (MFE) stopped within 0.3 x ATR(H4) short of / around a level (hindsight, shows the mechanism)"""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape as S1  # noqa: E402
import env_ctx as EC  # noqa: E402
B = S1.B; T = S1.T; H, L, N = S1.H, S1.L, S1.N
C1 = list(B.C1); C4 = list(B.C4); A4 = EC._A
def piv(R, CL):
    P = sorted(((CL[e['available_idx']], e['price']) for e in R['pivot_events']), key=lambda x: x[0]); return [p for _, p in P], [t for t, _ in P]
P4, P4T = piv(B.R4, C4); P1, P1T = piv(B.R1, C1)
if __name__ == '__main__':
    TR, yrs = S1.load_all(); rows = []
    for nm, t in TR.items():
        for x in t.itertuples():
            s = x.side; ie = min(x.ie, N - 1)
            if x.i0 >= ie:
                continue
            fav = (H[x.i0:ie] - x.entry) / x.risk if s == 1 else (x.entry - L[x.i0:ie]) / x.risk
            mfe = fav.max()
            if mfe < 1:
                continue
            te = T[x.i0]; k4 = bisect.bisect_right(C4, te) - 1; a4 = A4[k4] / x.risk
            out = {}
            for nmx, P, PT, n in (('H4', P4, P4T, 60), ('H1', P1, P1T, 120)):
                j = bisect.bisect_right(PT, te); lv = np.array(P[max(0, j - n):j]); d = s * (lv - x.entry) / x.risk
                ahead = np.sort(d[(d > 1) & (d <= 4)])
                out[f'lvl_{nmx}'] = ahead[0] if len(ahead) else np.nan
                out[f'n_{nmx}'] = len(ahead)
                out[f'peak_{nmx}'] = bool(np.any(np.abs(d - mfe) <= 0.3 * a4) or np.any((d > mfe) & (d - mfe <= 0.3 * a4)))
            rows.append(dict(ea=nm, lose=x.R <= 0, R=x.R, mfe=mfe, **out))
    d = pd.DataFrame(rows)
    print(f'+1R到達 {len(d)}回、負け {d.lose.mean():.0%}')
    for tf in ('H4', 'H1'):
        print(f'== {tf} の節目（エントリー前に確定した高値・安値）')
        g = pd.cut(d[f'lvl_{tf}'].fillna(9), [1, 1.5, 2, 3, 4, 10], labels=['1〜1.5R', '1.5〜2R', '2〜3R', '3〜4R', '4R以内に無し'])
        print(d.groupby(g, observed=True).agg(n=('R', 'size'), 負け率=('lose', 'mean'), 平均R=('R', 'mean'), 合計R=('R', 'sum')).round(2).to_string())
        print(' 伸びの頂点が節目に当たった:', d.groupby(f'peak_{tf}').agg(n=('R', 'size'), 負け率=('lose', 'mean'), 平均R=('R', 'mean')).round(2).to_dict('index'))
    d.to_csv(B.HERE / 'results' / 'resist_features.csv', index=False)
