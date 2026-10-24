"""Features of every H4 W event (for matching the user's W judgement and for filtering pattern A).
All values use only bars up to the neck-break bar (causal). Writes results/w_features.csv."""
import json, glob, sys, bisect
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(Path(__file__).parent))
from env_recognition.data import load
from env_recognition.ea_api import TF_LEN
from env_recognition import dow_trend
from env_recognition.pivots import atr, pivot_events
from long_features import stage_arrays

h4 = load('H4', 'long').reset_index(drop=True)
A = atr(h4); T = pd.to_datetime(h4.t); C4 = list(T + TF_LEN['H4'])
r = dow_trend.run(h4, 'H4')
big = {K: dow_trend.run(h4, 'H4', events=pivot_events(h4, th=K * A)) for K in (3.0, 4.5)}
stg = {K: stage_arrays(big[K], len(h4)) for K in big}
H, L, C = (h4[z].to_numpy(float) for z in 'hlc')
s75 = h4.c.rolling(75).mean().to_numpy(); s200 = h4.c.rolling(200).mean().to_numpy()
ep = lambda i: int((T[i] - pd.Timestamp('1970-01-01')) // pd.Timedelta(seconds=1))
J = {}
for f in glob.glob(str(Path(__file__).parent / 'feedback' / 'wjudge' / '*.json')):
    d = json.load(open(f)); J[d['t']] = d['v']
rows = []
for e in r['w_events']:
    k = e['idx']; bot = e['action'] == 'W_BOTTOM'; s = 1 if bot else -1; want = 'down' if bot else 'up'
    a_, b_, c_ = e['a_anchor'], e['b_anchor'], e['c_anchor']; at = A[a_]; w0 = max(0, a_ - 90)
    run = (H[w0:a_].max() - e['a']) / at if bot else (e['a'] - L[w0:a_].min()) / at
    spd = abs(e['b'] - e['a']) / at / max(1, b_ - a_)
    # neck touches: separate visits of price to the B level (within 0.3 ATR) from A to the break, excluding the B swing itself
    band = 0.3 * at; vis = 0; inside = False
    for i in range(a_ + 1, k):
        hit = (H[i] >= e['b'] - band) if bot else (L[i] <= e['b'] + band)
        if hit and not inside and abs(i - b_) > 1:
            vis += 1
        inside = hit
    row = dict(t=ep(k), date=T[k].strftime('%Y-%m-%d %H:%M'), yr=T[k].year, kind='底' if bot else '天', v=J.get(ep(k)),
               spd=spd, ac=abs(e['a'] - e['c']) / at, run=run, ab_bars=b_ - a_, bc_bars=c_ - b_,
               ma200_far=bool(s * (s200[k - 1] - C[k - 1]) > 0), ma75_far=bool(s * (s75[k - 1] - C[k - 1]) > 0),
               d200=s * (s200[k - 1] - C[k - 1]) / at, neck_touch=vis)
    for K in big:
        row[f'big{K}_against'] = big[K]['bars'][k - 1][0] == want
        row[f'big{K}_stage'] = int(stg[K][k - 1]) if big[K]['bars'][k - 1][0] == want else -1
    row['good_shape'] = spd >= 0.45 and row['ac'] <= 2
    rows.append(row)
X = pd.DataFrame(rows)
X.to_csv(Path(__file__).parent / 'results' / 'w_features.csv', index=False)
if __name__ == '__main__':
    Y = X[X.v.notna()].copy(); Y['ok'] = Y.v == 'ok'
    print('W全体', len(X), '判定', len(Y), '○率', round(Y.ok.mean(), 2))
    for c in ['ma200_far', 'ma75_far', 'big3.0_against', 'big4.5_against', 'good_shape']:
        a, b = Y[Y[c]], Y[~Y[c]]
        print(f'{c:16s} はい {len(a)}件 ○率{a.ok.mean():.2f} | いいえ {len(b)}件 ○率{b.ok.mean() if len(b) else float("nan"):.2f}')
    for c in ['big3.0_stage', 'big4.5_stage', 'neck_touch']:
        print(c, Y.groupby(c).ok.agg(['count', 'mean']).round(2).to_dict('index'))
