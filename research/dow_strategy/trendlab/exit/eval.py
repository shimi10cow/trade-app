import pandas as pd, numpy as np, glob
d = pd.concat([pd.read_pickle(f) for f in glob.glob('/home/user/trendlab/exit/e_*.pkl')])
V = ['H1_0.5', 'H1_1', 'H1_1.5', 'H1_2', 'M15_1', 'M15_2', 'M15_3', 'H4_1', 'H4_2', 'HYB', 'BE']
OWN = {'S@BTCUSD': 'H1_2', 'T@US30': 'M15_2', 'T2@EURUSD': 'M15_2', 'DS@JP225': 'H1_1.5', 'DS@US500': 'H1_1.5', 'DS@XAUUSD': 'H1_1.5', 'Q@XAGUSD': 'H4_1'}
SP = {'US30': '2020-07-01', 'US500': '2021-10-01', 'JP225': '2021-10-01', 'BTCUSD': '2022-01-01'}
d['h2'] = [t >= pd.Timestamp(SP.get(s, '2016-01-01')) for s, t in zip(d.sym, d.t)]
def t(r): return r.mean() / (r.std(ddof=1) / np.sqrt(len(r)))
def dd(x, col):
    r = x.sort_values('t')[col].to_numpy(); eq = np.cumsum(r); return (np.maximum.accumulate(np.r_[0, eq])[1:] - eq).max()
pd.set_option('display.width', 250)
print('reproduction:', ', '.join(f"{k} {x.R.mean():+.2f}/{x[OWN.get(k, 'H1_1')].mean():+.2f}" for k, x in d.groupby('key')))
avg = d.groupby('key')[V].mean().round(2)
print('\n1 回平均 R（各 EA × 決済）'); print(avg.assign(今=[OWN.get(k, 'H1_1') for k in avg.index]).to_string())
rows = []
for k, x in d.groupby('key'):
    own = OWN.get(k, 'H1_1'); base = x[own]
    for v in V:
        r = x[v]; a, b = x[~x.h2][v].mean(), x[x.h2][v].mean(); a0, b0 = x[~x.h2][own].mean(), x[x.h2][own].mean()
        rows.append(dict(EA=k, 今=own, 決済=v, 回数=len(r), 平均=r.mean(), 差=r.mean() - base.mean(), t=t(r), 今t=t(base), 前半差=a - a0, 後半差=b - b0,
                         勝率=(r > 0).mean(), 今勝率=(base > 0).mean(), DD=dd(x, v), 今DD=dd(x, own)))
o = pd.DataFrame(rows)
good = o[(o.前半差 > 0.03) & (o.後半差 > 0.03) & (o.決済 != o.今)].sort_values('差', ascending=False)
print('\n前後半とも +0.03R 以上良くなる決済（EA ごとに最大 3 つ）:')
print(good.groupby('EA').head(3).round(2).to_string(index=False))
o.to_pickle('/home/user/trendlab/exit/eval.pkl')
