"""Score pivot rules against the user's hand-labelled swings (labels/eurusd_dow_annotations_v14.json).

recall    = share of user points matched by a same-kind engine pivot within ±tol bars
precision = share of engine pivots (inside the labelled window) matched by a user point
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from .data import load
from .pivots import pivot_events, final_pivots, indicators, K

LABELS = Path(__file__).with_name('labels') / 'eurusd_dow_annotations_v14.json'


def labels(tf, df):
    raw = json.loads(LABELS.read_text())['swingByTF'][tf]
    t = ((pd.to_datetime(df.t) - pd.Timestamp('1970-01-01')) // pd.Timedelta(milliseconds=1)).to_numpy()
    pos = {int(x): i for i, x in enumerate(t)}
    out = sorted({(pos[ms], k) for ms, k in raw if ms in pos})
    missing = sum(ms not in pos for ms, _ in raw)
    return out, missing


def threshold(df, tf=None, k=None):
    return indicators(df, k=K if k is None else k)[1]


def match(lab, piv, tol=2):
    """Greedy nearest same-kind matching. Returns (user_flags, engine_list, engine_flags)."""
    if not lab:
        return [], [], []
    lo, hi = lab[0][0] - tol, lab[-1][0] + tol
    eng = [(p['idx'], p['kind']) for p in piv if lo <= p['idx'] <= hi]
    used = {}
    uflag = []
    for i, k in lab:
        best = None
        for j, (e, ek) in enumerate(eng):
            if ek == k and j not in used and abs(e - i) <= tol and (best is None or abs(e - i) < abs(eng[best][0] - i)):
                best = j
        if best is not None:
            used[best] = i
        uflag.append(best is not None)
    return uflag, eng, [j in used for j in range(len(eng))]


def score(lab, piv, tol=2):
    if not lab:
        return dict(recall=np.nan, precision=np.nan, f1=np.nan)
    uf, eng, ef = match(lab, piv, tol)
    r = sum(uf) / len(lab); p = sum(ef) / max(len(eng), 1)
    return dict(recall=r, precision=p, f1=2 * r * p / max(r + p, 1e-12), n_user=len(lab), n_engine=len(eng))


def evaluate(tf, tol=2, k=None, outside_bar=True):
    df = load(tf)
    lab, _ = labels(tf, df)
    piv = final_pivots(pivot_events(df, tf, th=threshold(df, k=k), outside_bar=outside_bar))
    return score(lab, piv, tol)
