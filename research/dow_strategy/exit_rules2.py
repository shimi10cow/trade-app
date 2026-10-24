"""Exit by shape v2: which structure (M15 / H1, provisional / major) and WHEN it may close the trade.
  cond  all      : always
        neg      : only if the trade is under water when the shape appears (cut before -1R)
        neg_nr   : under water AND never reached +0.5R (the trade never worked)
        stall1/2 : trade reached +1R / +2R, then gave back >= half of it, then the shape appears (take the rest)
Prints, per rule: trades closed by it, their original R vs new R, the 5-EA total and 5-year blocks.
Also prints path stats (MFE vs final R)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import exit_rules as E1  # noqa: E402
B = E1.B; T = E1.T; H, L, C = E1.H, E1.L, E1.C; N = E1.N; COST = E1.COST
EV = {('m15' + k[0], k[1]): v for k, v in E1.EV.items()}
C1 = pd.DatetimeIndex(B.C1)
def h1map(idx):
    return np.unique(np.clip(T.searchsorted(C1[np.asarray(idx)]) - 1, 0, N - 1))
tmp = {}
for e in B.R1['prov_events']:
    if e['action'] in ('REVERSAL', 'PROV_START'):
        tmp.setdefault(('h1prov', e['to']), []).append(e['idx'])
for e in B.R1['events']:
    if e.get('machine') == 'major' and e['action'] == 'REVERSAL':
        tmp.setdefault(('h1major', e['to']), []).append(e['idx'])
for k, v in tmp.items():
    EV[k] = h1map(v)
BL = ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))


def apply(tr, src, cond):
    out = []; fired_n = 0; orig = 0.0; new = 0.0
    for x in tr.itertuples():
        s = x.side; R = x.R; ie = min(x.ie, N - 1)
        arr = EV.get((src, 'down' if s == 1 else 'up'), np.array([], int))
        j = np.searchsorted(arr, x.i0)
        while x.i0 < ie and j < len(arr) and arr[j] < ie:
            i = arr[j]; j += 1
            seg = H[x.i0:i + 1] if s == 1 else L[x.i0:i + 1]
            mfe = s * ((seg.max() if s == 1 else seg.min()) - x.entry) / x.risk
            cur = s * (C[i] - x.entry) / x.risk
            ok = (cond == 'all' or (cond == 'neg' and cur < 0) or (cond == 'neg_nr' and cur < 0 and mfe < 0.5)
                  or (cond.startswith('stall') and mfe >= int(cond[-1]) and cur <= mfe / 2))
            if ok:
                nr = cur - COST / x.risk; fired_n += 1; orig += R; new += nr; R = nr
                break
        out.append(R)
    return np.array(out), fired_n, orig, new


if __name__ == '__main__':
    TR = {n: E1.load(n, f) for n, f in E1.FILES}
    yrs = {}
    for n, t in TR.items():
        y = pd.DatetimeIndex(np.asarray(T)[t.i0.clip(upper=N - 1).to_numpy()]).year.to_numpy()
        TR[n] = t[y >= 2005].reset_index(drop=True); yrs[n] = y[y >= 2005]
    print('== 経路: 最大順行(MFE)と最終R')
    for n, t in TR.items():
        mfe = np.array([x.side * ((H[x.i0:max(x.i0 + 1, x.ie)].max() if x.side == 1 else L[x.i0:max(x.i0 + 1, x.ie)].min()) - x.entry) / x.risk for x in t.itertuples()])
        w = t.R > 0
        print(f'  {n}: 勝ち{w.sum()} 平均+{t.R[w].mean():.2f}R(最大順行の平均{mfe[w].mean():.2f}R) / 負け{(~w).sum()} 平均{t.R[~w].mean():.2f}R'
              f'（すぐ負け=MFE<0.3: {np.mean(mfe[~w] < 0.3):.0%}） / 勝ち全体で+3R以上{np.mean(t.R > 3):.0%}')
    print('== 途中決済 (発動数: 元のR合計→新しいR合計) | 5本合計 | 5年ブロック')
    for src in ('m15prov', 'm15major', 'h1prov', 'h1major'):
        for cond in ('all', 'neg', 'neg_nr', 'stall1', 'stall2'):
            tot = 0; fn = 0; o = 0; nw = 0; b = np.zeros(5); parts = []
            for n, t in TR.items():
                r, f_, o_, n_ = apply(t, src, cond); y = yrs[n]
                tot += r.sum(); fn += f_; o += o_; nw += n_
                b += [r[(y >= a) & (y <= z)].sum() for a, z in BL]; parts.append(f'{n}{r.sum() - t.R.sum():+.0f}')
            print(f'  {src:8s} {cond:7s} 発動{fn:4d}: {o:+7.1f}→{nw:+7.1f} | 合計{tot:+6.1f}R | ' + ' '.join(f'{v:+.0f}' for v in b) + ' | 差 ' + ' '.join(parts))
