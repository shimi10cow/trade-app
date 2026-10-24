"""Calibrate a pullback counter to the user's labels. Side = H1 provisional Dow trend.
Reset when the side flips or H1 closes beyond SMA75 against the side ('H1 correction' -> next leg starts at 0).
A pullback counts once its confirmed swing is at least k x ATR(H1) deep from the running extreme; count = pushes made
after such pullbacks (+1 = current pullback number); a mark against the side, or before any push since reset = 'bo'."""
import sys, json, glob, bisect, numpy as np, pandas as pd
sys.path.insert(0, '.')
from env_recognition.data import load
from env_recognition import dow_trend
from env_recognition.ea_api import TF_LEN
from env_recognition.pivots import atr
S = sys.argv[1]
M = pd.DataFrame([json.load(open(f)) for f in glob.glob(S + '/db_jpy3/missed/*.json')]).sort_values('t').reset_index(drop=True)
P = json.load(open(S + '/viewer_jpy/data/pbc.json'))
def auto(t, side, base):
    R = P[base]; T = [r[0] for r in R]; j = bisect.bisect_right(T, t) - 1
    s, n = R[j][1], R[j][2]; return 'bo' if s != side else str(min(n + 1, 4))
L = {'H1': 3600, 'H4': 14400, 'M15': 900}
M['tc'] = M.t + M.tf.map(L)
M['label'] = M.pb.where(M.pb.notna(), [auto(t, s, 'H4' if tf == 'H4' else 'H1') for t, s, tf in zip(M.tc, M.side, M.tf)]).replace({'rev': 'bo'})
M.to_pickle(S + '/tdiag/marks_all.pkl')
print(M.groupby('year').size().to_dict(), M.tf.value_counts().to_dict()); print(pd.crosstab(M.year, M.label))
df = load('H1', 'long').reset_index(drop=True); R = dow_trend.run(df, 'H1')
ts = ((pd.to_datetime(df.t) + TF_LEN['H1'] - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).to_numpy()
h, l, c = (df[z].to_numpy(float) for z in 'hlc'); A = np.asarray(atr(df)); m75 = df.c.rolling(75).mean().to_numpy()
prv = [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['prov_bars']]
def run(k, use75):
    st = np.zeros((len(df), 3), int); side = 0; n = 0; ext = h[0]; armed = False; pend = None
    for i in range(len(df)):
        s = prv[i]
        reset = s != side or (use75 and np.isfinite(m75[i]) and s * (c[i] - m75[i]) < 0)
        if reset:
            side, n, armed, pend = s, 0, False, None; ext = h[i] if s == 1 else l[i]
        # pullback depth from the running extreme, measured on the bar's extreme
        dep = (ext - l[i]) if side == 1 else (h[i] - ext)
        if dep >= k * A[i]: armed = True
        if side == 1 and h[i] > ext:
            ext = h[i]; n += armed; armed = False
        elif side == -1 and l[i] < ext:
            ext = l[i]; n += armed; armed = False
        st[i] = (side, n, armed)
    return st
M = M[M.tf == "H1"].reset_index(drop=True); lab = M.label.to_numpy()
for use75 in (False, True):
    for k in (0.5, 1, 1.5, 2, 3, 4):
        st = run(k, use75); pred = []
        for m in M.itertuples():
            j = np.searchsorted(ts, m.tc, 'right') - 1; s, n, a = st[j]
            pred.append('bo' if s != m.side or (n == 0 and not a) else str(min(n + a, 4)))
        pred = np.array(pred); ok = (pred == lab).mean()
        near = np.mean([(a == b) or (a.isdigit() and b.isdigit() and abs(int(a) - int(b)) <= 1) for a, b in zip(pred, lab)])
        u = M.pb.notna().to_numpy(); oku = (pred[u] == lab[u]).mean()
        print(f'手入力のみ一致 {oku:.0%} | SMA75リセット={use75} k={k}: 一致 {ok:.0%}  ±1以内 {near:.0%}  予測分布 {pd.Series(pred).value_counts().sort_index().to_dict()}', flush=True)
