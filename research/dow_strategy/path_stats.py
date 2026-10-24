"""Why is the total small? Per EA: win rate, avg win/loss, MFE of winners vs what was kept, losers that first ran +0.5/+1R,
and what a perfect 'exit at 50% of MFE' would leave (upper bound for any exit logic)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_shape as S1  # noqa: E402
H, L, N = S1.H, S1.L, S1.N
TR, yrs = S1.load_all()
for nm, t in TR.items():
    mfe = np.array([x.side * ((H[x.i0:max(x.i0 + 1, x.ie)].max() if x.side == 1 else L[x.i0:max(x.i0 + 1, x.ie)].min()) - x.entry) / x.risk for x in t.itertuples()])
    r = t.R.to_numpy(); w = r > 0; n = len(r); yrs_n = len(set(yrs[nm]))
    print(f'[{nm}] {n}回({n / yrs_n:.0f}/年) 勝率{w.mean():.0%} 平均勝ち+{r[w].mean():.2f} 平均負け{r[~w].mean():.2f} 期待値{r.mean():+.2f}R')
    print(f'    勝ちトレード: 最大含み益の平均{mfe[w].mean():.2f}R → 確定{r[w].mean():.2f}R（取れた割合{r[w].sum() / mfe[w].sum():.0%}）'
          f' / 確定+3R以上 {np.mean(r >= 3):.0%} が 利益の{r[r >= 3].sum() / r[w].sum():.0%}')
    print(f'    負けトレード: すぐ負け(含み益<0.3R) {np.mean(mfe[~w] < 0.3):.0%} / +0.5R以上から負け {np.mean(mfe[~w] >= 0.5):.0%}'
          f' / +1R以上から負け {np.mean(mfe[~w] >= 1):.0%}（その負け合計{r[~w & (mfe >= 1)].sum():+.0f}R）')
    print(f'    参考: 含み益+1R到達率 {np.mean(mfe >= 1):.0%} / +2R {np.mean(mfe >= 2):.0%} / +3R {np.mean(mfe >= 3):.0%}')
