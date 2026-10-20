"""Per-year trade JSON for the viewer's EA switch: data/pf_{year}.json (same fields as the existing-EA trades + src,
mfe = best unrealised R before exit, mae = worst), plus data/pf_all.json (compact list for the per-EA summary).
Usage: EA_M15_CACHE=<m15 csv> python build_pf_trades.py <out data dir> <years...>"""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
D = Path(__file__).parent / 'results'
SRC = [('R', 'regime2_R2c.csv', 'レンジ型押し目'), ('T', 'regime2_T1t.csv', 'トレンド型押し目'), ('L', 'tl_N2.csv', 'ライン3〜4点目'), ('A', 'retest_N1.csv', 'H4転換リターン'), ('C', 'step2/cl15_md4tri.csv', 'M15調整ライン抜け')]
sec = lambda ts: int((pd.Timestamp(ts) - pd.Timestamp('1970-01-01')) // pd.Timedelta(seconds=1))
m = pd.read_csv(os.environ['EA_M15_CACHE']); MT = pd.to_datetime(m.time).to_numpy(); MH = m.high.to_numpy(); ML = m.low.to_numpy()
rows = []
for code, f, lab in SRC:
    d = pd.read_csv(D / f)
    for x in d.itertuples():
        if 'Rc' in d:
            t, xt, R, sl = x.time, x.ExitTime, x.Rc, x.initial_sl
            i0 = MT.searchsorted(np.datetime64(pd.Timestamp(t))) + 1
        else:
            t, xt, R, sl = x.t, x.exit_t, x.R, x.entry - x.side * x.risk
            i0 = MT.searchsorted(np.datetime64(pd.Timestamp(t)))
        ie = max(i0 + 1, MT.searchsorted(np.datetime64(pd.Timestamp(xt))))
        s = int(x.side)
        hi, lo = MH[i0:ie].max(), ML[i0:ie].min()
        mfe = (hi - x.entry if s == 1 else x.entry - lo) / x.risk; mae = (lo - x.entry if s == 1 else x.entry - hi) / x.risk
        rows.append(dict(t=sec(t), side=s, p=0, entry=round(float(x.entry), 5), sl=round(float(sl), 5), xt=sec(xt),
                         xp=round(float(x.exit), 5), R=round(float(R), 2), risk=round(float(x.risk) / 1e-4, 1),
                         stg='RTLAC'.index(code), nrev=0, trail='', d1=None, h4=None, h1=None, src=code, srcl=lab,
                         mfe=round(float(mfe), 2), mae=round(float(mae), 2)))
out = Path(sys.argv[1]); years = [int(y) for y in sys.argv[2:]]
allc = []
for y in years:
    T = sorted([r for r in rows if pd.Timestamp(r['t'], unit='s').year == y], key=lambda r: r['t'])
    for n, r in enumerate(T, 1):
        r['n'] = n
        allc.append([y, r['src'], r['R'], r['mfe'], r['t'], r['side'], n])
    (out / f'pf_{y}.json').write_text(json.dumps(T, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
(out / 'pf_all.json').write_text(json.dumps(dict(names={c: l for c, _, l in SRC}, tr=allc), ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
print(len(allc), 'trades')
