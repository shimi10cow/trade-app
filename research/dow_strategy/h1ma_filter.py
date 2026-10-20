"""Entry filter from the user's 'いらない' marks: skip entries on the wrong side of H1 SMA75 (and variants)."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape as S1  # noqa: E402
import user_marks_study as U  # noqa: E402  (feats)
B = S1.B; T = S1.T; N = S1.N; BL = S1.BL
TR, yrs = S1.load_all()
rows = []
for nm, t in TR.items():
    for x, y in zip(t.itertuples(), yrs[nm]):
        tt = T[min(x.i0, N - 1)]
        f = U.feats(tt, x.side)
        rows.append(dict(ea=nm, y=y, R=x.R, **f))
D = pd.DataFrame(rows)
def show(lab, m):
    out = []
    for nm in ('R', 'T', 'L', 'A', 'C', '全体'):
        d = D[m] if nm == '全体' else D[m & (D.ea == nm)]
        r = d.R; w = r > 0
        out.append(f'{nm}:{len(r)}回{r.sum():+.0f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f}')
    d = D[m]; b = [d.R[(d.y >= a) & (d.y <= z)].sum() for a, z in BL]
    eq = d.sort_index().R.cumsum().to_numpy()
    print(f'{lab:30s} ' + ' '.join(out) + ' | ' + ' '.join(f'{v:+.0f}' for v in b))
show('全部', D.R == D.R)
for th in (-1.0, -0.5, 0.0, 0.5):
    show(f'H1 SMA75 の有利側 {th:+}ATR以上', D.h1ma75 >= th)
show('外した分(H1 SMA75 の逆側)', D.h1ma75 < 0)
show('H1 SMA200 の有利側', D.h1ma200 >= 0)
show('H1 75も200も有利側', (D.h1ma75 >= 0) & (D.h1ma200 >= 0))
D.to_csv(B.HERE / 'results' / 'h1ma_feats.csv', index=False)
