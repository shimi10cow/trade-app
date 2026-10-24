"""Risk allocation and position caps (2026-10-21). Inputs: list of (EA, pair, trade file). Everything decided on 2005-2015,
checked on 2016-2026. Overall risk scaled so the FIRST-half max DD = -20%.
  weights : equal | by first-half mean R / std R (Sharpe-like, clipped 0.5-2x) | by first-half PF-1
  caps    : max simultaneous open trades (all) and per currency (EUR, USD, JPY, GBP exposure count)"""
import sys, json
from pathlib import Path
import numpy as np, pandas as pd
RES = Path(__file__).parent / 'results'
DIRS = {'EURUSD': RES, 'USDJPY': RES / 'usdjpy', 'EURJPY': RES / 'eurjpy', 'GBPUSD': RES / 'gbpusd'}
def load(ea, pair, f):
    d = pd.read_csv(DIRS[pair] / f)
    x = pd.DataFrame(dict(R=d.Rc, tt=pd.to_datetime(d.time), et=pd.to_datetime(d.ExitTime))) if 'Rc' in d else pd.DataFrame(dict(R=d.R, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t)))
    x = x[x.tt.dt.year >= 2005].copy(); x['ea'] = ea; x['pair'] = pair; return x
def simulate(T, w, risk, lo, hi, cap=None, ccap=None):
    d = T[(T.tt.dt.year >= lo) & (T.tt.dt.year <= hi)].sort_values('tt')
    if cap or ccap:
        keep = []; open_ = []
        for x in d.itertuples():
            open_ = [o for o in open_ if o[0] > x.tt]
            cur = [x.pair[:3], x.pair[3:]]
            if cap and len(open_) >= cap: continue
            if ccap and any(sum(c in o[1] for o in open_) >= ccap for c in cur): continue
            open_.append((x.et, cur)); keep.append(x.Index)
        d = d.loc[keep]
    d = d.sort_values('et'); r = d.R.to_numpy() * d.key.map(w).to_numpy()
    eq = np.cumprod(1 + risk * r); pk = np.maximum.accumulate(np.r_[1, eq])[1:]
    yr = pd.Series(risk * r).groupby(d.et.dt.year.to_numpy()).apply(lambda g: np.prod(1 + g) - 1)
    return eq[-1] ** (1 / (hi - lo + 1)) - 1, (eq / pk - 1).min(), yr.min(), len(d) / (hi - lo + 1)
def evaluate(T, w, cap=None, ccap=None, dd=-0.20):
    a, b = 0.0005, 0.05
    for _ in range(25):
        m = (a + b) / 2
        if simulate(T, w, m, 2005, 2015, cap, ccap)[1] < dd: b = m
        else: a = m
    return a, simulate(T, w, a, 2005, 2015, cap, ccap), simulate(T, w, a, 2016, 2026, cap, ccap)
def weights(T, mode):
    f = T[T.tt.dt.year <= 2015]; w = {}
    for k, g in f.groupby('key'):
        r = g.R
        if mode == 'equal': w[k] = 1.0
        elif mode == 'sharpe': w[k] = r.mean() / r.std() if r.std() > 0 else 0
        elif mode == 'pf': w[k] = max(0.0, r[r > 0].sum() / max(1e-9, -r[r <= 0].sum()) - 1)
    m = np.mean([v for v in w.values() if v > 0]) or 1
    return {k: float(np.clip(v / m, 0.5, 2.0)) if mode != 'equal' else 1.0 for k, v in w.items()}
def report(lab, items, extra=()):
    T = pd.concat([load(*it) for it in items], ignore_index=True); T['key'] = T.ea + '@' + T.pair
    print(f'### {lab}（{len(items)}本）')
    print('| 配分 | 上限 | リスク/回(基準) | 前半 年平均 | 後半 年平均 | 後半 最大DD | 後半 最悪年 | 後半 回/年 | 年平均÷DD |')
    for wm in ('equal', 'sharpe', 'pf'):
        w = weights(T, wm)
        for cap, ccap in ((None, None), (4, None), (6, None), (None, 2), (None, 3)) + tuple(extra):
            r, a, b = evaluate(T, w, cap, ccap)
            print(f'| {wm} | 全体{cap or "-"}/通貨{ccap or "-"} | {r:.2%} | {a[0]:.1%} | **{b[0]:.1%}** | {b[1]:.1%} | {b[2]:.1%} | {b[3]:.0f} | {b[0] / -b[1]:.2f} |', flush=True)
    return T
if __name__ == '__main__':
    items = json.loads(sys.argv[1]) if len(sys.argv) > 1 else [
        ['R', 'EURUSD', 'regime2_R2c.csv'], ['T', 'EURUSD', 'regime2_T1t.csv'], ['L', 'EURUSD', 'tl_N2.csv'], ['A', 'EURUSD', 'retest_N1.csv'],
        ['C', 'EURUSD', 'step2/cl15_md4tri.csv'], ['C', 'USDJPY', 'step2/cl15_md4tri.csv'], ['J2', 'USDJPY', 'turn/jt2_h1major+hour0_10.csv']]
    report(sys.argv[2] if len(sys.argv) > 2 else '現行', items)
