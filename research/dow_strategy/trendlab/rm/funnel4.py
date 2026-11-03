import sys
from collections import Counter
sym = sys.argv[1]
src = open('run4.py').read().replace("sym = sys.argv[1]", f"sym = '{sym}'").split("rows = []; busy = {}")[0]
exec(src)
tol = 0.2
for kind in ('PRV', 'MAJ'):
    C = Counter()
    for t4, s, L, kd, k4e, kprev in ev:
        if kd != kind: continue
        k4 = bisect.bisect_right(C4, t4) - 1; a4 = A4[k4]
        if not np.isfinite(a4) or a4 <= 0: continue
        i0 = int(np.searchsorted(T, np.datetime64(t4)))
        if i0 >= n: continue
        C['1 H4転換'] += 1
        if k4e - kprev < 50: continue
        C['2 前のトレンド50本以上'] += 1
        ib0 = int(np.searchsorted(T, np.datetime64(t4) - np.timedelta64(4, 'h')))
        if next((i for i in range(ib0, i0) if (c[i] - L) * s > 0), None) is None: C['x ブレイク足なし'] += 1; continue
        peak = 0.0; peak_i = None; touch = None; dead = False
        for i in range(i0, min(i0 + 96 * 10, n)):
            if s * (c[i] - L) < -tol * a4: dead = True; break
            ex_ = ((h[i] - L) if s == 1 else (L - l[i])) / a4
            if ex_ > peak: peak, peak_i = ex_, i
            if peak >= 1.0 and i > peak_i and ((l[i] <= L + 0.3 * a4) if s == 1 else (h[i] >= L - 0.3 * a4)) and (i - i0) >= 24:
                touch = i; break
        if dead: C['x 戻る前にレベルを割った' + ('（山1ATR未満）' if peak < 1 else '（山あり）')] += 1; continue
        if touch is None: C['x 10日以内に戻ってこない' + ('（山1ATR未満）' if peak < 1 else '')] += 1; continue
        C['3 山を作ってレベルに戻った'] += 1
        lst = turn[s]; q = int(np.searchsorted(lst, touch)); why = 'x 48時間以内に転換なし'
        for i in range(touch, min(touch + 192, n)):
            if s * (c[i] - L) < -tol * a4: why = 'x 戻った後にレベルを割った'; break
            if s * (c[i] - L) > 1.5 * a4: why = 'x 転換前に1.5ATR走った'; break
            if q < len(lst) and lst[q] <= i: why = '4 M15転換で入る'; break
        C[why] += 1
    print(sym, kind, dict(sorted(C.items())), flush=True)
