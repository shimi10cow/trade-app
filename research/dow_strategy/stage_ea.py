"""Trend-stage EAs (user 2026-10-19): existing MA+Stoch entry, filtered by the H4 Dow trend stage.

Design (decided before running):
  develop on 2020-2024, final check once on 2025-2026, 2015-2019 shown for reference.
  H4 stage = BREAKOUTs (close beyond the latest swing high/low) since the last H4 REVERSAL.
  recent reversals = H4 REVERSALs in the last 90 H4 bars (~15 trading days)  -> range measure
Variants (all require H4 major trend == trade side):
  初動            stage 0
  レンジ明け初動  stage 0 and recent reversals >= 2
  中盤            stage 1-2 and recent reversals <= 1
  終盤除外        stage 0-2
  初動＋中盤      stage 0, or stage 1-2 with recent reversals <= 1
Each runs on two bases: existing EA (long MAs on) and long MAs off. Cost 1.2 pip.
Usage: EA_M15_CACHE=<broker-time csv> python dow_strategy/stage_ea.py
"""
import bisect
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / 'core')); sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine_m15 as E  # noqa: E402
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
from long_features import stage_arrays  # noqa: E402

COST = 1.2e-4
OUT = Path(__file__).with_name('results')
h4 = load('H4', 'long').reset_index(drop=True)
res = dow_trend.run(h4, 'H4')
TREND = [b[0] for b in res['bars']]
STAGE = stage_arrays(res, len(h4))
REV = sorted(e['idx'] for e in res['events'] if e.get('machine') == 'major' and e['action'] == 'REVERSAL')
CLOSE = list(pd.to_datetime(h4.t) + TF_LEN['H4'])


def h4_info(t):
    k = bisect.bisect_right(CLOSE, t + pd.Timedelta(minutes=15)) - 1
    nrev = bisect.bisect_right(REV, k) - bisect.bisect_right(REV, k - 90)
    return k, TREND[k], int(STAGE[k]), nrev


RULES = {
    '初動': lambda s, n: s == 0,
    'レンジ明け初動': lambda s, n: s == 0 and n >= 2,
    '中盤': lambda s, n: 1 <= s <= 2 and n <= 1,
    '終盤除外': lambda s, n: 0 <= s <= 2,
    '初動＋中盤': lambda s, n: s == 0 or (1 <= s <= 2 and n <= 1),
}


def make_filter(rule):
    f = RULES[rule]

    def ok(t, side):
        k, tr, s, n = h4_info(t)
        return k >= 0 and tr == ('up' if side == 1 else 'down') and f(s, n)
    return ok


def stats(r):
    if not len(r):
        return dict(n=0)
    w = r > 0
    eq = np.cumsum(r)
    return dict(n=len(r), win=round(w.mean(), 3), sumR=round(r.sum(), 1), PF=round(r[w].sum() / max(1e-9, -r[~w].sum()), 2),
                maxDD=round((eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min(), 1))


def run(job):
    base, rule = job
    kw = dict(use_long_ma=(base == '長期MAあり'))
    if rule != '基準':
        kw['extra_filter'] = make_filter(rule)
    tr = E.run_pair('EURUSD', E.Config(**kw))
    tr['Rc'] = tr.R - COST / tr.risk
    y = pd.to_datetime(tr.time).dt.year
    out = {}
    for lab, a, b in (('開発2020-24', 2020, 2024), ('確認2025-26', 2025, 2026), ('参考2015-19', 2015, 2019)):
        out[lab] = stats(tr.Rc[(y >= a) & (y <= b)].to_numpy())
    for yr in range(2020, 2025):
        out[str(yr)] = round(tr.Rc[y == yr].sum(), 1)
    tr.to_csv(OUT / f'stage_ea_trades_{base}_{rule}.csv', index=False)
    return base, rule, out


if __name__ == '__main__':
    jobs = [(b, r) for b in ('長期MAあり', '長期MAなし') for r in ['基準', *RULES]]
    rows = {}
    with Pool(4) as pool:
        for base, rule, out in pool.imap(run, jobs):
            rows[f'{base}｜{rule}'] = out
            d, c, p = out['開発2020-24'], out['確認2025-26'], out['参考2015-19']
            print(f"{base}｜{rule:8s} 開発 n={d['n']} {d.get('sumR', 0):+.1f}R PF{d.get('PF', 0)} DD{d.get('maxDD', 0)} "
                  f"| 年別 {[out[str(y)] for y in range(2020, 2025)]} | 確認 n={c['n']} {c.get('sumR', 0):+.1f}R PF{c.get('PF', 0)} "
                  f"| 参考 n={p['n']} {p.get('sumR', 0):+.1f}R PF{p.get('PF', 0)}", flush=True)
    flat = {k: {f'{p}_{m}': v[p].get(m) for p in ('開発2020-24', '確認2025-26', '参考2015-19') for m in ('n', 'sumR', 'PF', 'maxDD')}
            | {y: v[y] for y in map(str, range(2020, 2025))} for k, v in rows.items()}
    pd.DataFrame(flat).T.to_csv(OUT / 'stage_ea_summary.csv')
