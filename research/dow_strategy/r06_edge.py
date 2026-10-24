"""Step 2 (R at range score > 0.6): which extra condition keeps most trades but removes the weak ones?
Features at entry (causal): env ctx, H4 triangle forming, H1/H4 trend vs side, entry hour (broker time), point type."""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_ctx as EC  # noqa: E402
import dow_turn_ea as B  # noqa: E402
C1 = list(B.C1); C4 = list(B.C4)
d = pd.read_csv(B.HERE / 'results' / 'regime2_R2a.csv'); d['time'] = pd.to_datetime(d.time); d = d[d.time.dt.year >= 2005].reset_index(drop=True)
rows = []
for x in d.itertuples():
    tc = x.time + pd.Timedelta(minutes=15); s = x.side; dd = 'up' if s == 1 else 'down'
    k1 = bisect.bisect_right(C1, tc) - 1; k4 = bisect.bisect_right(C4, tc) - 1
    c = EC.ctx_at(tc, s)
    rows.append(dict(**c, tri4=EC.tri_active(tc, 'H4'), tri1=EC.tri_active(tc, 'H1'),
                     h1=B.R1['bars'][k1][0] == dd, h1p=B.R1['prov_bars'][k1][0] == dd, h4=B.R4['bars'][k4][0] == dd, h4p=B.R4['prov_bars'][k4][0] == dd,
                     hour=x.time.hour, slp=x.risk / 1e-4))
F = pd.DataFrame(rows); F['R'] = d.Rc; F['y'] = d.time.dt.year
BL = ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))
def show(name, m):
    r = F.R[m]; y = F.y[m]; w = r > 0
    b = [r[(y >= a) & (y <= z)].sum() for a, z in BL]
    print(f'{name:28s} n={len(r):4d} {r.sum():+6.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} 期待値{r.mean():+.2f} | ' + ' '.join(f'{v:+.0f}' for v in b) + ('  ★' if min(b) > 0 else ''))
show('R スコア>0.6 (全部)', F.R == F.R)
show('  スコア>0.7 (今の採用)', F.rs > 0.7)
for c in ('tri4', 'tri1', 'h1', 'h1p', 'h4', 'h4p'):
    show(f'  {c}=True', F[c]); show(f'  {c}=False', ~F[c])
for c, q in (('sd', None), ('er', None), ('sh', None), ('d75', None), ('slp', None)):
    qs = F[c].quantile([1 / 3, 2 / 3]).to_numpy()
    show(f'  {c} 低(<{qs[0]:.2f})', F[c] < qs[0]); show(f'  {c} 中', (F[c] >= qs[0]) & (F[c] < qs[1])); show(f'  {c} 高(>={qs[1]:.2f})', F[c] >= qs[1])
for lo, hi in ((0, 7), (7, 10), (10, 15), (15, 19), (19, 24)):
    show(f'  時間 {lo}-{hi}時', (F.hour >= lo) & (F.hour < hi))
print('--- 組み合わせ')
nt = ~F.tri4
show('notri', nt)
show('notri + sh<1.5', nt & (F.sh < 1.5))
show('notri + sh<2', nt & (F.sh < 2))
show('notri + H1仮=順', nt & F.h1p)
show('notri + er<0.07', nt & (F.er < 0.07))
show('notri + sh<2 + H1仮=順', nt & (F.sh < 2) & F.h1p)
show('notri + sh<2 + er<0.07', nt & (F.sh < 2) & (F.er < 0.07))
show('スコア>0.7 + notri', nt & (F.rs > 0.7))
show('スコア>0.7 + notri + sh<2', nt & (F.rs > 0.7) & (F.sh < 2))
