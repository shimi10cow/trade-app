"""Event study (no M15): what happens after a touch / break of user-style trendlines, 2005-2026, by era.
Outcome = signed close-to-close move after H bars in the line direction (ATR units) + MFE/MAE before 1 ATR stop.
Usage: python dow_strategy/tl_study.py [H4|H1]"""
import bisect, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load
from env_recognition import dow_trend
from env_recognition.pivots import atr

TF = sys.argv[1] if len(sys.argv) > 1 else 'H4'
ULOOK = {'H4': 20, 'H1': 40}[TF]; MAXLEN = 500
df = load(TF, 'long').reset_index(drop=True)
R = dow_trend.run(df, TF); A = atr(df)
H, L, Cl = (df[z].to_numpy(float) for z in 'hlc'); T = pd.to_datetime(df.t)


def touches(band=0.25):
    last = {}
    for e in R['pivot_events']:
        last[e['id']] = e
    piv = sorted((e['idx'], e['kind'], e['price'], e['available_idx']) for e in last.values())
    byk = {k: [p for p in piv if p[1] == k] for k in ('hi', 'lo')}
    byk_i = {k: [p[0] for p in v] for k, v in byk.items()}
    n = len(df); out = []
    for ia, kind, pa, _ in piv:
        up = kind == 'lo'; j0 = max(0, ia - ULOOK)
        if (up and L[j0:ia].size and L[j0:ia].min() < pa) or ((not up) and H[j0:ia].size and H[j0:ia].max() > pa):
            continue
        lo_, hi_ = bisect.bisect_right(byk_i[kind], ia), bisect.bisect_right(byk_i[kind], ia + MAXLEN)
        later = sorted(byk[kind][lo_:hi_], key=lambda p: p[3])
        slope = b = None; q = 0; depth = None; nt = 2; away = True
        for j in range(ia + 1, min(n, ia + MAXLEN)):
            while q < len(later) and later[q][3] <= j:
                pb = later[q]; sl = (pb[2] - pa) / (pb[0] - ia)
                if slope is None or (sl < slope if up else sl > slope):
                    if slope is None:
                        seg = H[ia:pb[0] + 1] if up else L[ia:pb[0] + 1]
                        pk = seg.max() if up else seg.min()
                        depth = (pk - pb[2]) / max(1e-9, pk - pa) if up else (pb[2] - pk) / max(1e-9, pa - pk)
                    slope, b = sl, pb
                q += 1
            if (L[j] < pa) if up else (H[j] > pa):
                break
            if slope is None:
                continue
            v = pa + slope * (j - ia)
            base = dict(j=j, s=1 if up else -1, ia=ia, angle=abs(slope) / A[ia], depth=depth, trend=R['bars'][j][0], n=nt)
            if (Cl[j] < v) if up else (Cl[j] > v):
                out.append(dict(base, kind='break')); break
            bd = band * A[j]
            if not away and ((L[j] - v) if up else (v - H[j])) > A[j]:
                away = True
            if away and j > b[0] + 1 and ((L[j] <= v + bd) if up else (H[j] >= v - bd)):
                nt += 1; away = False
                out.append(dict(base, kind='touch', n=nt))
    return pd.DataFrame(out)


def outcome(ev, s_col='s', HZ=(10, 30)):
    n = len(Cl); rows = []
    for _, e in ev.iterrows():
        j = int(e.j); s = e[s_col]
        if j + max(HZ) >= n:
            rows.append({}); continue
        r = {f'f{h}': s * (Cl[j + h] - Cl[j]) / A[j] for h in HZ}
        # 1-ATR stop vs reaching +2 ATR first (within 60 bars)
        res = 0
        for k in range(j + 1, min(n, j + 61)):
            if (L[k] <= Cl[j] - A[j]) if s == 1 else (H[k] >= Cl[j] + A[j]):
                res = -1; break
            if (H[k] >= Cl[j] + 2 * A[j]) if s == 1 else (L[k] <= Cl[j] - 2 * A[j]):
                res = 2; break
        r['r2'] = res
        rows.append(r)
    return pd.concat([ev.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


ev = outcome(touches())
ev['yr'] = T[ev.j].dt.year.to_numpy()
ev['blk'] = pd.cut(ev.yr, [2002, 2009, 2014, 2019, 2024, 2026], labels=['03-09', '10-14', '15-19', '20-24', '25-26'])
ev.to_csv(Path(__file__).parent / 'results' / f'tl_study_{TF}.csv', index=False)
pd.set_option('display.width', 200)


def summ(x):
    return pd.Series(dict(n=len(x), f10=x.f10.mean(), f30=x.f30.mean(), r2=x.r2.mean()))

t = ev[ev.kind == 'touch']
print(TF, 'touch / impulse(trend==d) / n=3-4 / angle>=0.03 / depth 0.3-0.85')
imp = t[(t.trend == np.where(t.s == 1, 'up', 'down'))]
good = imp[(imp.n.between(3, 4)) & (imp.angle >= 0.03) & imp.depth.between(0.3, 0.85)]
for nm, x in [('all touch', t), ('impulse', imp), ('good 3-4', good), ('good n3', good[good.n == 3]),
              ('good depth .38-.62', good[good.depth.between(.38, .62)]), ('impulse n>=5', imp[imp.n >= 5]),
              ('counter-trend lines', t[t.trend != np.where(t.s == 1, 'up', 'down')])]:
    print('==', nm); print(x.groupby('blk', observed=True).apply(summ).round(2).T.to_string())
b = ev[ev.kind == 'break'].copy(); b['s'] = -b.s
b = outcome(b.drop(columns=['f10', 'f30', 'r2']))
b['blk'] = pd.cut(T[b.j].dt.year.to_numpy(), [2002, 2009, 2014, 2019, 2024, 2026], labels=['03-09', '10-14', '15-19', '20-24', '25-26'])
for nm, x in [('break after n>=3 (trade break dir)', b[b.n >= 3]), ('break n>=3 good', b[(b.n >= 3) & (b.angle >= .03)]), ('break n<=2', b[b.n <= 2])]:
    print('==', nm); print(x.groupby('blk', observed=True).apply(summ).round(2).T.to_string())
