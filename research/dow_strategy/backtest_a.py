"""Prototype backtest: Pattern A (trend-follow on M15 Dow reversal), EURUSD 2025-01..2026-10.

Spec: research/env_recognition/METHOD_DOW_DRAFT.md (user answers 2026-10-18)
  trigger : M15 MAJOR trend reversal in direction d (close beyond M15 protected swing)
  filter  : H4 major trend == d (pattern A; D1 agreement is a score item, pattern A3 allows D1 against)
  entry   : open of the next M15 bar
  stop    : the new M15 protected swing (low for buys) - 1 pip
  target  : nearest active H4 zone beyond entry (its near edge); none -> 3R
  costs   : 1.0 pip round trip
Score items (recorded, not required):
  d1      D1 major trend == d
  h4_back M15 reversal swing within 0.5 x ATR(H4) of an H4 level (protected swing or active zone)
  imp     M15 reversal swing within 0.3 x ATR(H4) of a live H4/D1 impulse line
  ma      H1 SMA20 vs SMA75 in direction d, SMA75 sloping d (vs 5 bars ago), price on the right side of SMA75
  h4corr  a live H4 correction line (against d) is broken
  m15corr a live M15 correction line (against d) is broken
Everything uses only bars closed before the entry bar (EnvRecognizer.state_at).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import EnvRecognizer, TF_LEN  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402

PIP = 0.0001
COST = 1.0 * PIP


def run(start='2025-03-01', tp='zone_or_high', trigger='major'):
    frames = {tf: load(tf) for tf in ('D1', 'H4', 'H1', 'M15')}
    env = EnvRecognizer(frames)
    m15 = env.tf['M15']
    df = m15['df']
    o, h, l, c = (df[z].to_numpy(float) for z in 'ohlc')
    t = pd.to_datetime(df.t)
    h1 = frames['H1'].reset_index(drop=True)
    s20, s75 = h1.c.rolling(20).mean(), h1.c.rolling(75).mean()
    h4atr = atr(frames['H4'].reset_index(drop=True))
    m15_brk = [x for x in m15['lines']['events'] if x['action'] == 'break']
    m15_dir = {ln['key']: ln['direction'] for ln in m15['lines']['lines']}
    h4res = env.tf['H4']['res']
    trades = []
    if trigger == 'prov':
        # provisional-trend changes (pattern start or provisional reversal); stop = provisional protected
        evs = [dict(x, broken_anchor=x.get('broken_anchor', x['idx'])) for x in m15['res']['prov_events']
               if x['action'] in ('REVERSAL', 'PROV_START')]
        stop_bars = m15['res']['prov_bars']
    else:
        evs = [x for x in m15['res']['events'] if x['action'] == 'REVERSAL']
        stop_bars = m15['res']['bars']
    for e in evs:
        k = e['idx']
        if t[k] < pd.Timestamp(start) or k + 1 >= len(df):
            continue
        d = e['to']
        sgn = 1 if d == 'up' else -1
        ts = t[k] + TF_LEN['M15']                 # close of the reversal bar = open of entry bar
        st = env.state_at(ts)
        h4, d1 = st['H4'], st['D1']
        if h4 is None or h4['trend'] != d:
            continue
        stop_lvl = stop_bars[k][1]                # new M15 (provisional) protected swing
        entry = o[k + 1]
        stop = stop_lvl - sgn * PIP
        risk = sgn * (entry - stop)
        if risk <= 0:
            continue
        a4 = h4atr[env.last_closed('H4', ts)]
        # target: nearest H4 zone beyond entry
        tgt = [z['bottom'] if d == 'up' else z['top'] for z in h4['zones']
               if (z['bottom'] > entry if d == 'up' else z['top'] < entry)]
        # latest confirmed H4 swing in direction d (the high to retest for buys)
        kk = env.last_closed('H4', ts)
        sw = [p for p in h4res['pivots'].values() if p['kind'] == ('hi' if d == 'up' else 'lo') and p['known_at'] <= kk
              and sgn * (p['price'] - entry) > 0]
        if sw:
            tgt.append(max(sw, key=lambda p: p['idx'])['price'])
        if tp == 'zone_or_high':
            target = (min(tgt) if d == 'up' else max(tgt)) if tgt else entry + sgn * 3 * risk
        else:
            target = entry + sgn * float(tp) * risk
        if sgn * (target - entry) <= 0:
            continue
        # score items
        levels = [h4['protected']] + [z['top'] if d == 'up' else z['bottom'] for z in h4['zones']]
        h4_back = any(abs(stop_lvl - lv) <= 0.5 * a4 for lv in levels if lv is not None)
        imp = any(ln['cls'] == 'impulse' and abs(stop_lvl - ln['value']) <= 0.3 * a4
                  for s in (h4, d1) if s for ln in s['lines'])
        j = env.last_closed('H1', ts)
        ma = bool(j >= 80 and sgn * (s20[j] - s75[j]) > 0 and sgn * (s75[j] - s75[j - 5]) > 0
                  and sgn * (h1.c[j] - s75[j]) > 0)
        h4corr = any(ln['cls'] == 'correction' and ln['broken'] for ln in h4['lines'])
        # M15 correction line (against d) broken during the leg that led to this reversal
        leg0 = e['broken_anchor']
        m15corr = any(x['action'] == 'break' and leg0 <= x['idx'] <= k and m15_dir.get(x['key']) != d
                      for x in m15_brk)
        # simulate exits on following M15 bars (stop first if both touched)
        res, exit_i = None, None
        for i in range(k + 1, len(df)):
            if (l[i] <= stop) if d == 'up' else (h[i] >= stop):
                res, exit_i = -1.0, i; break
            if (h[i] >= target) if d == 'up' else (l[i] <= target):
                res, exit_i = sgn * (target - entry) / risk, i; break
        if res is None:
            res, exit_i = sgn * (c[-1] - entry) / risk, len(df) - 1
        res -= COST / risk
        trades.append(dict(time=t[k + 1], dir=d, entry=entry, stop=stop, target=target,
                           risk_pips=risk / PIP, rr=sgn * (target - entry) / risk, R=res,
                           bars=exit_i - k, d1=d1['trend'] == d if d1 else False, h4_back=h4_back,
                           imp=imp, ma=ma, h4corr=h4corr, m15corr=m15corr))
    T = pd.DataFrame(trades)
    T['score'] = T[['d1', 'h4_back', 'imp', 'ma', 'h4corr', 'm15corr']].sum(axis=1)
    return T


def summary(T):
    def s(x):
        if not len(x):
            return dict(n=0)
        w = x.R > 0
        pf = x.R[w].sum() / max(1e-9, -x.R[~w].sum())
        eq = x.R.cumsum()
        return dict(n=len(x), win=round(w.mean(), 2), sumR=round(x.R.sum(), 1), avgR=round(x.R.mean(), 2),
                    PF=round(pf, 2), maxDD=round((eq - eq.cummax()).min(), 1))
    rows = {'全体': s(T)}
    for col in ['d1', 'h4_back', 'imp', 'ma', 'h4corr', 'm15corr']:
        rows[f'{col}=あり'] = s(T[T[col]])
        rows[f'{col}=なし'] = s(T[~T[col]])
    for sc in sorted(T.score.unique()):
        rows[f'スコア{sc}'] = s(T[T.score == sc])
    for sc in (2, 3, 4):
        rows[f'スコア{sc}以上'] = s(T[T.score >= sc])
    return pd.DataFrame(rows).T


if __name__ == '__main__':
    T = run(tp=sys.argv[1] if len(sys.argv) > 1 else 'zone_or_high', trigger=sys.argv[2] if len(sys.argv) > 2 else 'major')
    out = Path(__file__).with_name('results')
    out.mkdir(exist_ok=True)
    T.to_csv(out / f'pattern_a_trades_{sys.argv[1:] and "_".join(sys.argv[1:]) or "default"}.csv', index=False)
    S = summary(T)
    S.to_csv(out / 'pattern_a_summary.csv')
    print(S.to_string())
