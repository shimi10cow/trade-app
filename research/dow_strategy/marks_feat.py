"""Features at each user mark (USDJPY) + forward path, using H1/H4 data of the workspace this runs in."""
import sys, json, glob, bisect, numpy as np, pandas as pd
sys.path.insert(0, '.'); sys.path.insert(0, 'dow_strategy')
from env_recognition.data import load
from env_recognition import dow_trend
from env_recognition.ea_api import TF_LEN
from env_recognition.pivots import atr
from gen_pbcount import Pushes
S = sys.argv[1]
M = pd.DataFrame([json.load(open(f)) for f in glob.glob(S + '/db_jpy2/missed/*.json')]).sort_values('t').reset_index(drop=True)
P = json.load(open(S + '/viewer_jpy/data/pbc.json'))
def auto(t, side, base):
    R = P[base]; T = [r[0] for r in R]; j = bisect.bisect_right(T, t) - 1
    s, n = R[j][1], R[j][2]; return 'bo' if s != side else str(min(n + 1, 4))
L = {'H1': 3600, 'H4': 14400, 'M15': 900}
M['tc'] = M.t + M.tf.map(L)
M['auto_now'] = [auto(t, s, 'H4' if tf == 'H4' else 'H1') for t, s, tf in zip(M.tc, M.side, M.tf)]
M['label'] = M.pb.where(M.pb.notna(), M.auto_now).replace({'rev': 'bo'})
M['labeled_by'] = np.where(M.pb.notna(), 'user', 'auto(accepted)')
feat = {}
for tf in ('H1', 'H4'):
    df = load(tf, 'long').reset_index(drop=True); R = dow_trend.run(df, tf)
    ts = ((pd.to_datetime(df.t) + TF_LEN[tf] - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).to_numpy()
    c = df.c; a = atr(df)
    m20, m75, m200 = c.rolling(20).mean(), c.rolling(75).mean(), c.rolling(200).mean()
    maj = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['bars']])
    prv = np.array([1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['prov_bars']])
    feat[tf] = dict(ts=ts, c=c.to_numpy(), h=df.h.to_numpy(), l=df.l.to_numpy(), a=np.asarray(a), m20=m20.to_numpy(), m75=m75.to_numpy(), m200=m200.to_numpy(), maj=maj, prv=prv)
rows = []
for m in M.itertuples():
    r = {}
    for tf, F in feat.items():
        j = np.searchsorted(F['ts'], m.tc, 'right') - 1; s = m.side; A = F['a'][j]
        r[tf + '_ma'] = int(np.sign(F['m20'][j] - F['m75'][j]) * s)
        r[tf + '_maj'] = int(F['maj'][j] * s); r[tf + '_prv'] = int(F['prv'][j] * s)
        r[tf + '_d20'] = round(s * (m.p - F['m20'][j]) / A, 2); r[tf + '_d75'] = round(s * (m.p - F['m75'][j]) / A, 2)
        r[tf + '_d200'] = round(s * (m.p - F['m200'][j]) / A, 2)
        if tf == 'H1':  # forward path in H1 ATR: best move and worst move over next 24/72 bars
            for n in (24, 72):
                hi, lo = F['h'][j + 1:j + 1 + n], F['l'][j + 1:j + 1 + n]
                fav = (hi.max() - m.p) if s == 1 else (m.p - lo.min()); adv = (m.p - lo.min()) if s == 1 else (hi.max() - m.p)
                r[f'mfe{n}'] = round(fav / A, 2); r[f'mae{n}'] = round(adv / A, 2)
    rows.append(r)
M = pd.concat([M, pd.DataFrame(rows)], axis=1)
M['jst'] = (pd.to_datetime(M.t, unit='s').dt.hour - 2 + 9) % 24  # broker (Athens, approx +2) -> JST; DST ignored
M.to_pickle(S + '/tdiag/marks_jpy_feat.pkl')
print(M.groupby('year').size().to_dict(), M.groupby(['year', 'side']).size().to_dict())
print(pd.crosstab(M.year, M.label)); print(pd.crosstab(M.year, M.labeled_by))
