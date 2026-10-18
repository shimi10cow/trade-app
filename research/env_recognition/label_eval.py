"""Score pivot rules against the user's hand-labelled swings (labels/eurusd_dow_annotations_v14.json).

recall    = share of user points matched by a same-kind engine pivot within ±tol bars
precision = share of engine pivots (inside the labelled window) matched by a user point
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data import load
from .pivots import pivot_events, final_pivots, PARAMS

LABELS = Path(__file__).with_name('labels') / 'eurusd_dow_annotations_v14.json'


def labels(tf, df):
    raw = json.loads(LABELS.read_text())['swingByTF'][tf]
    t = ((pd.to_datetime(df.t) - pd.Timestamp('1970-01-01')) // pd.Timedelta(milliseconds=1)).to_numpy()
    pos = {int(x): i for i, x in enumerate(t)}
    out = sorted({(pos[ms], k) for ms, k in raw if ms in pos})
    missing = sum(ms not in pos for ms, _ in raw)
    return out, missing


def threshold(df, tf, k=None, boost=None, cut=None):
    ap, k0, b0, c0 = PARAMS[tf]
    k = k0 if k is None else k; boost = b0 if boost is None else boost; cut = c0 if cut is None else cut
    h, l, c = (df[z].to_numpy(float) for z in 'hlc')
    pc = np.roll(c, 1)
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc))); tr[0] = h[0] - l[0]
    atr = pd.Series(tr).ewm(alpha=1 / ap, adjust=False).mean().to_numpy()
    noise = pd.Series(abs(np.diff(c, prepend=c[0]))).rolling(20).sum().to_numpy()
    er = np.zeros(len(c)); er[20:] = abs(c[20:] - c[:-20]) / np.maximum(noise[20:], 1e-12)
    return k * atr * np.where(er >= cut, 1 + boost, 1)


def score(lab, piv, tol):
    if not lab:
        return dict(recall=np.nan, precision=np.nan, f1=np.nan)
    lo, hi = lab[0][0] - tol, lab[-1][0] + tol
    eng = [(p['idx'], p['kind']) for p in piv if lo <= p['idx'] <= hi]
    used = set(); hit = 0
    for i, k in lab:
        best = None
        for j, (e, ek) in enumerate(eng):
            if ek == k and j not in used and abs(e - i) <= tol and (best is None or abs(e - i) < abs(eng[best][0] - i)):
                best = j
        if best is not None:
            used.add(best); hit += 1
    r = hit / len(lab); p = hit / max(len(eng), 1)
    return dict(recall=r, precision=p, f1=2 * r * p / max(r + p, 1e-12), n_user=len(lab), n_engine=len(eng))


def evaluate(tf, tol=2, **kw):
    df = load(tf)
    lab, _ = labels(tf, df)
    piv = final_pivots(pivot_events(df, tf, th=threshold(df, tf, **kw)))
    return score(lab, piv, tol)
