"""Forward selection over every EA variant we have (all instruments), judged ONLY on the first half (2005-2015):
start from the current 7 + gold L + gold S, add the variant that raises the first-half portfolio CAGR the most
(risk scaled so the first-half max DD = -20%), stop when the gain is < 0.5%/year. Second half (2016-2026) is reported
for checking only. BTC is excluded (no first-half data). Costs: FX 1.2 pip, gold 0.025%."""
import sys, glob, os
from pathlib import Path
from multiprocessing import Pool
import numpy as np, pandas as pd
import portfolio_opt as P
RES = P.RES
P.DIRS.update({'XAUUSD': RES / 'xauusd', 'EURJPY': RES / 'eurjpy', 'GBPUSD': RES / 'gbpusd'})
COST = {'XAUUSD': 2.5}
def load(ea, pair, f):
    d = pd.read_csv(P.DIRS[pair] / f)
    if 'Rc' in d and 'time' in d:
        x = pd.DataFrame(dict(R=d.Rc, tt=pd.to_datetime(d.time), et=pd.to_datetime(d.ExitTime)))
    elif 'R' in d and 't' in d and 'exit_t' in d:
        x = pd.DataFrame(dict(R=d.R, tt=pd.to_datetime(d.t), et=pd.to_datetime(d.exit_t)))
    else:
        return None
    if pair in COST and 'risk' in d:
        x['R'] = x.R - (COST[pair] - 1.2) * 1e-4 / d.risk
    x = x[(x.tt.dt.year >= 2005) & x.R.notna() & x.et.notna()].copy(); x['ea'] = ea; x['pair'] = pair
    return x
BASE = [['R', 'EURUSD', 'regime2_R2c.csv'], ['T', 'EURUSD', 'regime2_T1t.csv'], ['L', 'EURUSD', 'tl_N2.csv'], ['A', 'EURUSD', 'retest_N1.csv'],
        ['C', 'EURUSD', 'step2/cl15_md4tri.csv'], ['C', 'USDJPY', 'step2/cl15_md4tri.csv'], ['J2', 'USDJPY', 'turn/jt2_h1major+hour0_10.csv'],
        ['L', 'XAUUSD', 'tl_N2.csv'], ['S', 'XAUUSD', 'st2/S_ma_prov_buy_mt3_h1a1.csv']]
def cands():
    out = []
    for pair, d in P.DIRS.items():
        if pair == 'BTCUSD': continue
        root = Path(d)
        pats = ['*.csv', '*/*.csv'] if pair != 'EURUSD' else ['regime2_*.csv', 'tl_*.csv', 'retest_*.csv', 'step2/*.csv', 'turn/*.csv', 'session/*.csv', 'pb/*.csv', 'st/*.csv']
        for pat in pats:
            for f in root.glob(pat):
                rel = str(f.relative_to(root))
                if any(b[1] == pair and b[2] == rel for b in BASE) or 'summary' in rel or 'pick' in rel: continue
                out.append((pair, rel))
    return out
CACHE = {}
def get(pair, rel):
    k = (pair, rel)
    if k not in CACHE:
        CACHE[k] = load(rel.split('/')[-1][:-4], pair, rel)
    return CACHE[k]
CUR = None
def score(c):
    x = get(*c)
    if x is None or len(x[x.tt.dt.year <= 2015]) < 30: return c, None
    T = pd.concat([CUR, x.assign(ea=f'{c[0]}:{c[1]}')], ignore_index=True); T['key'] = T.ea + '@' + T.pair
    r, a, b = P.evaluate(T, {k: 1.0 for k in T.key.unique()})
    return c, (r, a[0], b[0], b[1], b[2])
if __name__ == '__main__':
    CUR = pd.concat([load(*b) for b in BASE], ignore_index=True); CUR['key'] = CUR.ea + '@' + CUR.pair
    r, a, b = P.evaluate(CUR, {k: 1.0 for k in CUR.key.unique()})
    print(f'出発点（9本）: リスク{r:.2%} 前半 年{a[0]:.1%} | 後半 年{b[0]:.1%} DD{b[1]:.1%} 最悪年{b[2]:.1%}', flush=True)
    C = cands(); print('候補', len(C), flush=True); best_a = a[0]; chosen = []
    for step in range(10):
        with Pool(4) as p:
            res = [x for x in p.map(score, C) if x[1] is not None]
        res.sort(key=lambda z: -z[1][1])
        top = res[0]
        print(f'  [{step + 1}] 上位5: ' + ' ; '.join(f'{c[0]} {c[1]} 前半{v[1]:.1%}/後半{v[2]:.1%}' for c, v in res[:5]), flush=True)
        if top[1][1] - best_a < 0.005: print('  伸びが0.5%未満なので終了'); break
        c, v = top; best_a = v[1]; chosen.append(c); C.remove(c)
        CUR = pd.concat([CUR, get(*c).assign(ea=f'{c[0]}:{c[1]}')], ignore_index=True); CUR['key'] = CUR.ea + '@' + CUR.pair
        print(f'追加 {step + 1}: {c[0]} {c[1]} → リスク{v[0]:.2%} 前半 年{v[1]:.1%} | 後半 年{v[2]:.1%} DD{v[3]:.1%} 最悪年{v[4]:.1%}', flush=True)
    pd.DataFrame(chosen, columns=['pair', 'file']).to_csv(RES / 'portfolio_greedy_chosen.csv', index=False)
