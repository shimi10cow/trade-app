import numpy as np, pandas as pd
from cyc6_throttle import paths, run
PA = paths(2005, 2026, n=2000)
print('| 1回のリスク | 減らし方 | 10年の年利(中央) | DD中央 | DD悪い方10% | -30%超の確率 |')
for risk in (0.005, 0.0075, 0.01, 0.0125):
    for lab, D, m in (('なし', 1, 1), ('DD10%超で半分', 0.10, 0.5), ('DD5%超で半分', 0.05, 0.5)):
        o = [run(r, risk, D, m) for r in PA]; dd = np.array([a for a, _ in o]); fin = np.array([b for _, b in o])
        print(f'| {risk:.2%} | {lab} | {np.median(fin)**0.1-1:.1%} | {np.median(dd):.0%} | {np.percentile(dd,10):.0%} | {(dd<-0.3).mean():.0%} |', flush=True)
