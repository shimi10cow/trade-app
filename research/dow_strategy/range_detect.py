"""Step 4 (2026-10-20): a fast, causal 'range' detector checked against the user's H4 state labels.
Labels (regime collection): up / down (impulse), adj (correction), range. For every labelled H4 bar we compute
causal features and measure how well each separates 'range' from 'up/down' (AUC, 0.5 = useless).
Usage: python range_detect.py <regime dump dir>"""
import sys, json, glob, bisect
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_ctx as EC  # noqa: E402
from env_recognition import dow_trend  # noqa: E402
h4 = EC._h4; c = EC._cv; A = EC._A; C4 = EC._C4; H = h4.h.to_numpy(float); L = h4.l.to_numpy(float)
R = dow_trend.run(h4, 'H4'); cs = pd.Series(c)
F = {}
for n in (20, 30, 50, 100, 200):
    F[f'er{n}'] = (cs.diff(n).abs() / cs.diff().abs().rolling(n).sum()).to_numpy()
for n in (30, 60):
    F[f'box{n}'] = ((pd.Series(H).rolling(n).max() - pd.Series(L).rolling(n).min()) / pd.Series(A)).to_numpy()
# number of major trend changes and of provisional/major disagreements over the last N bars
tr = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['bars']])
pv = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['prov_bars']])
chg = np.r_[0, (np.diff(tr) != 0).astype(int)]
for n in (30, 60, 120):
    F[f'flips{n}'] = pd.Series(chg).rolling(n).sum().to_numpy()
    F[f'disagree{n}'] = pd.Series((tr != pv).astype(int)).rolling(n).mean().to_numpy()
# bars since the last major breakout (trend progressing) and distance from SMA75 / slope of SMA75
bo = np.zeros(len(c)); last = -10**9
evb = {}
for e in R['events']:
    if e.get('machine') == 'major' and e['action'] in ('BREAKOUT', 'REVERSAL'):
        evb.setdefault(e['idx'], []).append(e['action'])
for i in range(len(c)):
    if 'BREAKOUT' in evb.get(i, []):
        last = i
    bo[i] = i - last
F['since_bo'] = np.minimum(bo, 500)
s75 = cs.rolling(75).mean()
F['absdev75'] = (np.abs(cs - s75) / pd.Series(A)).to_numpy()
F['slope75'] = (np.abs(s75 - s75.shift(10)) / pd.Series(A)).to_numpy()


def auc(pos, neg):
    pos, neg = np.asarray(pos), np.asarray(neg)
    pos, neg = pos[np.isfinite(pos)], neg[np.isfinite(neg)]
    if not len(pos) or not len(neg):
        return np.nan
    allv = np.r_[pos, neg]; r = pd.Series(allv).rank().to_numpy()
    return (r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


if __name__ == '__main__':
    G = [json.load(open(f)) for f in glob.glob(sys.argv[1] + '/*.json')]
    lab = np.array([None] * len(c), dtype=object)
    for g in sorted(G, key=lambda g: g['t2'] - g['t1'], reverse=True):        # nested labels: shorter wins
        if g['kind'] not in ('up', 'down', 'adj', 'range'):
            continue
        k1 = bisect.bisect_right(C4, pd.Timestamp(g['t1'], unit='s')) - 1; k2 = bisect.bisect_right(C4, pd.Timestamp(g['t2'], unit='s')) - 1
        lab[max(0, k1):k2 + 1] = g['kind']
    m = lab != None  # noqa: E711
    print('印の付いた H4 足:', int(m.sum()), pd.Series(lab[m]).value_counts().to_dict())
    rng = lab == 'range'; trd = np.isin(lab, ['up', 'down']); adj = lab == 'adj'
    rows = []
    for k, v in F.items():
        rows.append(dict(feature=k, AUC_レンジvs推進=auc(v[rng], v[trd]), AUC_調整vs推進=auc(v[adj], v[trd]),
                         レンジ中央=np.nanmedian(v[rng]), 推進中央=np.nanmedian(v[trd]), 調整中央=np.nanmedian(v[adj])))
    d = pd.DataFrame(rows); d['強さ'] = (d['AUC_レンジvs推進'] - 0.5).abs()
    pd.set_option('display.width', 200)
    print(d.sort_values('強さ', ascending=False).round(3).to_string(index=False))
    np.save(Path(__file__).with_name('results') / 'h4_labels.npy', lab)


def range_score():
    """Causal 0..1 score, high = range-like: average of (1 - percentile) of |dev75|, slope75, er50, ranks taken
    over the PAST only (expanding, 1500-bar warm-up) so it can be used in an EA."""
    out = np.full(len(c), np.nan)
    parts = []
    for k in ('absdev75', 'slope75', 'er50'):
        s = pd.Series(F[k])
        parts.append(1 - s.rolling(3000, min_periods=1500).rank(pct=True).to_numpy())
    return np.nanmean(np.vstack(parts), axis=0)


if __name__ == '__main__':
    rs = range_score(); np.save(Path(__file__).with_name('results') / 'h4_range_score.npy', rs)
    print('合成スコア AUC レンジvs推進', round(auc(rs[rng], rs[trd]), 3), ' 調整vs推進', round(auc(rs[adj], rs[trd]), 3))
    for th in (0.5, 0.6, 0.7):
        print(f' スコア>{th}: レンジの{np.mean(rs[rng] > th):.0%} / 推進の{np.mean(rs[trd] > th):.0%} / 調整の{np.mean(rs[adj] > th):.0%} がこの判定')
