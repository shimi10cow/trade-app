"""Exit by shape (user idea, 2026-10-20): re-simulate each EA's trades along M15 bars and close early when the M15
structure turns against the position. Early exit only shortens a trade, so applying it after the fact is exact
(the original stop/trail still applies until the rule fires). Uses only M15 bars closed after the entry.

  rules (long; mirror for short)
    prov   : M15 provisional trend turns down (pattern start or reversal of the provisional machine)
    major  : M15 major trend turns down (close through the M15 protected low)
    prov_lt1 / major_lt1 : same, only while the trade has not reached +1R yet (cut losers early, leave winners to the trail)
    prov_gt1 / major_gt1 : same, only once the trade has reached +1R (take profit on the 'stall' shape)
Also reports path stats: share of losers that were at >= +0.5R / +1R before losing.
Usage: DT_START=2005-01-01 DT_CACHE=... python exit_rules.py"""
import sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import dow_turn_ea as B  # noqa: E402
from portfolio import comp, D, report  # noqa: E402
T = B.T15; H, L, C = B.h, B.l, B.c; N = len(T); COST = B.COST
EV = {}
for e in B.R15['prov_events']:
    if e['action'] in ('REVERSAL', 'PROV_START'):
        EV.setdefault(('prov', e['to']), []).append(e['idx'])
for e in B.R15['events']:
    if e.get('machine') == 'major' and e['action'] == 'REVERSAL':
        EV.setdefault(('major', e['to']), []).append(e['idx'])
for k in EV:
    EV[k] = np.array(sorted(EV[k]))
FILES = [('R', 'regime2_R2c.csv'), ('T', 'regime2_T1t.csv'), ('L', 'tl_N2.csv'), ('A', 'retest_N1.csv'), ('C', 'step2/cl15_md4tri.csv')]


def load(name, f):
    d = pd.read_csv(D / f)
    if 'Rc' in d:     # engine trades: entry at the close of bar 'time'
        i0 = T.searchsorted(pd.to_datetime(d.time)) + 1; ie = T.searchsorted(pd.to_datetime(d.ExitTime)); R = d.Rc
    else:             # ea_core / tl / retest: entry at the open of bar 't'
        i0 = T.searchsorted(pd.to_datetime(d.t)); ie = T.searchsorted(pd.to_datetime(d.exit_t)); R = d.R
    return pd.DataFrame(dict(src=name, i0=i0, ie=ie, side=d.side, entry=d.entry, risk=d.risk, R=R))


def apply(tr, rule):
    out = []
    for x in tr.itertuples():
        s = x.side; R = x.R; ie = min(x.ie, N - 1)
        if rule != 'none' and x.i0 < ie:
            kind = rule.split('_')[0]; arr = EV.get((kind, 'down' if s == 1 else 'up'), np.array([]))
            j = np.searchsorted(arr, x.i0); fired = None
            while j < len(arr) and arr[j] < ie:
                i = arr[j]
                mfe = s * ((H[x.i0:i + 1].max() if s == 1 else L[x.i0:i + 1].min()) - x.entry) / x.risk
                if rule.endswith('lt1') and mfe >= 1:
                    j += 1; continue
                if rule.endswith('gt1') and mfe < 1:
                    j += 1; continue
                fired = i; break
            if fired is not None:
                R = s * (C[fired] - x.entry) / x.risk - COST / x.risk
        out.append(R)
    return np.array(out)


if __name__ == '__main__':
    TR = {n: load(n, f) for n, f in FILES}
    TR = {n: t[pd.DatetimeIndex(np.asarray(T)[t.i0.clip(upper=N - 1).to_numpy()]).year >= 2005].reset_index(drop=True) for n, t in TR.items()}
    print('== 負けトレードの途中経過（最大順行）')
    for n, t in TR.items():
        mfe = np.array([x.side * ((H[x.i0:max(x.i0 + 1, x.ie)].max() if x.side == 1 else L[x.i0:max(x.i0 + 1, x.ie)].min()) - x.entry) / x.risk for x in t.itertuples()])
        lose = t.R <= 0
        print(f'  {n}: 負け {lose.sum()}回のうち +0.5R以上伸びてから負け {np.mean(mfe[lose] >= 0.5):.0%}、+1R以上 {np.mean(mfe[lose] >= 1):.0%}／-0.9R以下の負けの平均 {t.R[t.R < -0.9].mean():.2f}R')
    print('== 途中決済ルール（R合計 / PF / 5年ブロック）')
    yrs = {n: pd.DatetimeIndex(np.asarray(T)[t.i0.clip(upper=N - 1).to_numpy()]).year.to_numpy() for n, t in TR.items()}
    for rule in ('none', 'prov', 'major', 'prov_lt1', 'major_lt1', 'prov_gt1', 'major_gt1'):
        line = []; tot = 0; allb = np.zeros(5)
        for n, t in TR.items():
            r = apply(t, rule); y = yrs[n]; tot += r.sum()
            b = np.array([r[(y >= a) & (y <= z)].sum() for a, z in ((2005, 2009), (2010, 2014), (2015, 2019), (2020, 2024), (2025, 2026))]); allb += b
            w = r > 0; line.append(f'{n}:{r.sum():+.0f}(PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f})')
        print(f'  {rule:10s} 合計{tot:+7.1f}R | ' + ' '.join(line) + ' | ' + ' '.join(f'{v:+.0f}' for v in allb))
