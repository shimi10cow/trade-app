"""EA #2 prototype: the user's discretionary style (from 22 model trades, 2026-10-19).

  direction : H4 major Dow trend d
  setup     : H1 is correcting (H1 major or provisional trend != d)          [opt: no H1 condition]
  trigger   : M15 trend turns to d (provisional or major reversal), entry at next M15 open
  stop      : beyond the new M15 protected swing + buffer x ATR7(H1)
  exit      : once +act R, trail to the latest confirmed H1 Dow swing (tighten only); stop first if both touched
  one open position per direction; cost 1.2 pip.
Periods: develop 2020-2024, check 2025, model-trade year 2026 (the model trades were never used to tune).
Also measures how many of the user's model trades it reproduces (same side, entry within +/-24h).
Usage: EA_M15_CACHE=<csv> python dow_strategy/dow_turn_ea.py
"""
import bisect
import glob
import json
import sys
from multiprocessing import Pool
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from env_recognition.data import load  # noqa: E402
from env_recognition.ea_api import TF_LEN  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
from env_recognition.pivots import atr  # noqa: E402

PIP, COST = 1e-4, 1.2e-4
HERE = Path(__file__).resolve().parent
import os
START = pd.Timestamp(os.environ.get('DT_START', '2019-06-01'))

print('prep...', flush=True)
def cut(df):
    return df[pd.to_datetime(df.t) >= START - pd.Timedelta(days=400)].reset_index(drop=True)
h4 = cut(load('H4', 'long')); h1 = cut(load('H1', 'long'))
m15 = load('M15', 'long'); m15 = m15[pd.to_datetime(m15.t) >= START - pd.Timedelta(days=30)].reset_index(drop=True)
import pickle
_cache = Path(os.environ.get('DT_CACHE', '/tmp')) / f"dowruns_{START.date()}.pkl"
if _cache.exists():
    R4, R1, R15 = pickle.load(open(_cache, 'rb'))
else:
    R4 = dow_trend.run(h4, 'H4'); R1 = dow_trend.run(h1, 'H1'); R15 = dow_trend.run(m15, 'M15')
    pickle.dump((R4, R1, R15), open(_cache, 'wb'))
C4 = list(pd.to_datetime(h4.t) + TF_LEN['H4']); C1 = list(pd.to_datetime(h1.t) + TF_LEN['H1'])
T15 = pd.to_datetime(m15.t); o, h, l, c = (m15[z].to_numpy(float) for z in 'ohlc')
A1 = atr(h1)
# confirmed H1 swings by the close time they became known
H1P = sorted(((C1[e['available_idx']], e['kind'], e['price']) for e in R1['pivot_events']), key=lambda x: x[0])
H1PT = [x[0] for x in H1P]
print('prep done', flush=True)


def signals(trigger):
    out = []
    if trigger in ('prov', 'both'):
        out += [(e['idx'], e['to'], 'prov') for e in R15['prov_events'] if e['action'] in ('REVERSAL', 'PROV_START')]
    if trigger in ('major', 'both'):
        out += [(e['idx'], e['to'], 'major') for e in R15['events'] if e['action'] == 'REVERSAL']
    return sorted(out)


def run(cfg):
    name, trigger, h1cond, buf, act = cfg[:5]
    flt = cfg[5] if len(cfg) > 5 else None
    sig = {}
    for k, d, src in signals(trigger):
        sig.setdefault(k, []).append((d, src))
    trades, pos = [], []
    for i in range(len(m15)):
        # manage open positions on bar i
        keep = []
        for p in pos:
            if p['k'] >= i:
                keep.append(p); continue
            s = p['side']
            if (l[i] <= p['sl']) if s == 1 else (h[i] >= p['sl']):
                p['exit'] = p['sl']; p['exit_t'] = T15[i]; trades.append(p); continue
            if not p['trail'] and s * ((h[i] if s == 1 else l[i]) - p['entry']) >= act * p['risk']:
                p['trail'] = True
            if p['trail']:
                j = bisect.bisect_right(H1PT, T15[i] + TF_LEN['M15']) - 1
                while j >= 0 and H1P[j][1] != ('lo' if s == 1 else 'hi'):
                    j -= 1
                if j >= 0:
                    v = H1P[j][2] - s * PIP
                    if (v < c[i]) if s == 1 else (v > c[i]):
                        p['sl'] = max(p['sl'], v) if s == 1 else min(p['sl'], v)
            keep.append(p)
        pos = keep
        if i not in sig or i + 1 >= len(m15) or T15[i] < START:
            continue
        T = T15[i] + TF_LEN['M15']                      # close of the signal bar
        k4 = bisect.bisect_right(C4, T) - 1; k1 = bisect.bisect_right(C1, T) - 1
        for d, src in sig[i]:
            s = 1 if d == 'up' else -1
            if R4['bars'][k4][0] != d or any(p['side'] == s for p in pos):
                continue
            if h1cond and R1['bars'][k1][0] == d and R1['prov_bars'][k1][0] == d:
                continue
            if flt is not None and not flt(i, d, k1, k4):
                continue
            bars = R15['prov_bars'] if src == 'prov' else R15['bars']
            swing = bars[i][1]
            if swing is None:
                continue
            entry = o[i + 1]
            sl = swing - s * buf * A1[k1]
            if s * (entry - sl) < 10 * PIP:
                sl = entry - s * 10 * PIP
            risk = s * (entry - sl)
            pos.append(dict(k=i + 1, t=T15[i + 1], side=s, entry=entry, sl=sl, risk=risk, trail=False, src=src))
    for p in pos:
        p['exit'] = c[-1]; p['exit_t'] = T15[len(m15) - 1]; trades.append(p)
    tr = pd.DataFrame(trades)
    tr['R'] = (tr.exit - tr.entry) * tr.side / tr.risk - COST / tr.risk
    return name, tr


def stats(r):
    if not len(r):
        return 'n=0'
    w = r > 0; eq = np.cumsum(r)
    dd = (eq - np.maximum.accumulate(np.r_[0, eq])[1:]).min()
    return f"n={len(r)} {r.sum():+.1f}R PF{r[w].sum() / max(1e-9, -r[~w].sum()):.2f} 勝率{w.mean():.0%} DD{dd:.1f}"


MODEL = [json.load(open(f)) for f in glob.glob(str(HERE / 'feedback' / 'model_trades' / '*.json'))]


def recall(tr):
    hit = {'real': [0, 0], 'ideal': [0, 0]}
    for m in MODEL:
        k = m.get('kind', 'real'); hit[k][1] += 1
        t = pd.Timestamp(m['t'], unit='s')
        if ((tr.side == m['side']) & ((tr.t - t).abs() <= pd.Timedelta(hours=24))).any():
            hit[k][0] += 1
    byset = {}
    for m in MODEL:
        st = m.get('setup') or '-'; t = pd.Timestamp(m['t'], unit='s')
        h = ((tr.side == m['side']) & ((tr.t - t).abs() <= pd.Timedelta(hours=24))).any()
        byset.setdefault(st, [0, 0]); byset[st][0] += int(h); byset[st][1] += 1
    sets = ' '.join(f"{k}:{v[0]}/{v[1]}" for k, v in sorted(byset.items()))
    return f"お手本再現 裁量{hit['real'][0]}/{hit['real'][1]} 理想{hit['ideal'][0]}/{hit['ideal'][1]}（分類別 {sets}）"


CFGS = [  # name, trigger, H1 correcting, stop buffer x ATR(H1), trail activation R
    ('A 仮転換・H1調整・余裕1.0・1R後トレール', 'prov', True, 1.0, 1.0),
    ('B 主要転換・H1調整・余裕1.0・1R後トレール', 'major', True, 1.0, 1.0),
    ('C 仮転換・H1条件なし・余裕1.0・1R後トレール', 'prov', False, 1.0, 1.0),
    ('D 仮転換・H1調整・余裕0.5・1R後トレール', 'prov', True, 0.5, 1.0),
    ('E 仮転換・H1調整・余裕1.0・2R後トレール', 'prov', True, 1.0, 2.0),
    ('F 主要転換・H1調整・余裕0.5・2R後トレール', 'major', True, 0.5, 2.0),
]

if __name__ == '__main__':
    with Pool(4) as pool:
        for name, tr in pool.imap(run, CFGS):
            y = tr.t.dt.year
            tr.to_csv(HERE / 'results' / f"dow_turn_{name.split()[0]}.csv", index=False)
            print(f"{name}\n   開発2020-24 {stats(tr.R[(y >= 2020) & (y <= 2024)].to_numpy())}"
                  f"\n   確認2025    {stats(tr.R[y == 2025].to_numpy())}\n   2026        {stats(tr.R[y == 2026].to_numpy())}"
                  f"\n   SL中央値{tr.risk.median() / PIP:.0f}pips 保有中央値{((tr.exit_t - tr.t).dt.total_seconds() / 3600).median():.0f}h  {recall(tr)}", flush=True)
