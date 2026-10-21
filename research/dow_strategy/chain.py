import sys, os, numpy as np, pandas as pd
sys.path.insert(0, 'dow_strategy')
import pb_ea as P
M = pd.read_pickle(os.environ['MARKS']); M = M[(M.tf == 'H1') & M.label.isin(['1', '2', '3', '4'])].copy()
M['tt'] = pd.to_datetime(M.t, unit='s')
st = P.counter(2.0)
# per H1 bar state lookup
CL = pd.DatetimeIndex(P.CL)
res = []
for m in M.itertuples():
    j = CL.searchsorted(m.tt + pd.Timedelta(hours=1), 'right') - 1
    s, n, armed, new = st[j]
    w = range(max(0, j - 12), min(len(st), j + 13))
    anyev = any(st[k][3] and st[k][0] == m.side for k in w)
    res.append(dict(year=m.year, lab=m.label, side_ok=s == m.side, armed=armed, ev12=anyev,
                    d75=m.side * (P.cc[j] - P.M75[j]) / P.A1[j], ma=np.sign(P.M20[j] - P.M75[j]) == m.side))
R = pd.DataFrame(res)
print(len(R), R[['side_ok', 'armed', 'ev12', 'ma']].mean().round(2).to_dict())
print('d75 quartiles at marks', R.d75.quantile([.1, .25, .5, .75]).round(2).to_dict())
# trades of the best variant near marks
tr = pd.read_csv('dow_strategy/results/pb/P2_n3_d2.5_h1swing.csv', parse_dates=['t', 'setup_t'])
lag = []
for m in M.itertuples():
    x = tr[(tr.side == m.side) & ((tr.setup_t - m.tt).abs() <= pd.Timedelta(hours=12))]
    if len(x): lag.append(((x.t.iloc[0] - m.tt).total_seconds() / 3600, (x.entry.iloc[0] * 100 - m.p) * m.side))
L = pd.DataFrame(lag, columns=['hours', 'yen'])
print('setups near marks that traded', len(L), L.describe().round(2).to_dict())
