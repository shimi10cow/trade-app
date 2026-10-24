"""Per-pair setting choice (2026-10-21): for each EA family, among its candidate settings pick the one with the largest
FIRST-half total R among those with first-half PF >= pf_min and >= n_min trades; report its second half next to the default.
Usage: python select_pair.py <pair> [pf_min] [n_min]"""
import sys, glob, json
from pathlib import Path
import numpy as np, pandas as pd
RES = Path(__file__).parent / 'results'
DIRS = {'EURUSD': RES, 'USDJPY': RES / 'usdjpy', 'EURJPY': RES / 'eurjpy', 'GBPUSD': RES / 'gbpusd'}
FAM = {'R': ['regime2_R*.csv'], 'T': ['regime2_T*.csv'], 'L': ['tl_[A-Z]*.csv'], 'A': ['retest_[A-Z]*.csv'],
       'C': ['step2/cl15_*.csv'], 'J': ['turn/turn_*.csv', 'turn/jt_*.csv', 'turn/jt2_*.csv', 'turn/j3_*.csv', 'session/ev_*.csv']}
DEF = {'R': 'regime2_R2c.csv', 'T': 'regime2_T1t.csv', 'L': 'tl_N2.csv', 'A': 'retest_N1.csv', 'C': 'step2/cl15_md4tri.csv', 'J': 'turn/jt2_h1major+hour0_10.csv'}
def load(f):
    d = pd.read_csv(f)
    x = pd.DataFrame(dict(R=d.Rc, tt=pd.to_datetime(d.time))) if 'Rc' in d else pd.DataFrame(dict(R=d.R, tt=pd.to_datetime(d.t)))
    return x[x.tt.dt.year >= 2005]
def pf(r): w = r > 0; return r[w].sum() / max(1e-9, -r[~w].sum())
def stats(x):
    y = x.tt.dt.year; a = x.R[y <= 2015]; b = x.R[y >= 2016]
    return dict(n1=len(a), R1=a.sum(), PF1=pf(a), n2=len(b), R2=b.sum(), PF2=pf(b))
if __name__ == '__main__':
    pair = sys.argv[1]; pf_min = float(sys.argv[2]) if len(sys.argv) > 2 else 1.15; n_min = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    base = DIRS[pair]; chosen = {}
    print(f'| {pair} | 候補数 | 選んだ設定 | 前半 回数/合計/PF | 後半 回数/合計/PF | 既定の設定の 後半合計/PF |')
    for fam, pats in FAM.items():
        cands = []
        for p in pats:
            for f in glob.glob(str(base / p)):
                if 'ctx' in f or 'study' in f or f.endswith('_summary.csv'): continue
                try:
                    s = stats(load(f))
                except Exception:
                    continue
                cands.append((Path(f).relative_to(base).as_posix(), s))
        ok = [c for c in cands if c[1]['PF1'] >= pf_min and c[1]['n1'] >= n_min]
        dflt = stats(load(base / DEF[fam])) if (base / DEF[fam]).exists() else None
        if not ok:
            print(f'| {fam} | {len(cands)} | なし（前半で基準を満たす設定なし） | - | - | {dflt["R2"]:+.0f}R / {dflt["PF2"]:.2f} |' if dflt else f'| {fam} | {len(cands)} | なし | - | - | - |'); continue
        f, s = max(ok, key=lambda c: c[1]['R1'])
        chosen[fam] = f
        print(f"| {fam} | {len(cands)} | {f} | {s['n1']} / {s['R1']:+.0f}R / {s['PF1']:.2f} | {s['n2']} / {s['R2']:+.0f}R / {s['PF2']:.2f} | " + (f"{dflt['R2']:+.0f}R / {dflt['PF2']:.2f} |" if dflt else '- |'))
    (RES / f'chosen_{pair}.json').write_text(json.dumps(chosen, indent=1))
