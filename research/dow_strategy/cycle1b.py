import sys
import numpy as np, pandas as pd
T = pd.read_pickle(sys.argv[1])
tt = T.tt.to_numpy(); et = T.et.to_numpy(); pr = T.pair.to_numpy(); sd = T.side.to_numpy(); ea = T.ea.to_numpy()
ns = np.zeros(len(T), int); no = np.zeros(len(T), int)
for p in np.unique(pr):
    ix = np.where(pr == p)[0]
    for i in ix:
        w = ix[(tt[ix] < tt[i]) & (et[ix] > tt[i]) & (ea[ix] != ea[i])]
        ns[i] = (sd[w] == sd[i]).sum(); no[i] = (sd[w] != sd[i]).sum()
T['ns'] = np.minimum(ns, 3); T['no'] = np.minimum(no, 2)
T.to_pickle(sys.argv[1].replace('.pkl', '_hold.pkl'))
print('他EAの同方向保有数別 平均R（前半/後半、回数）')
print(T.groupby(['ns', 'half']).R.agg(['mean', 'size']).unstack().round(3).to_string())
print('\n採用EAのみ'); A = T[T.adopted]
print(A.groupby(['ns', 'half']).R.agg(['mean', 'size']).unstack().round(3).to_string())
print('\n通貨別 （0本 vs 1本以上）平均R')
T['any'] = T.ns > 0
print(T.groupby(['pair', 'any', 'half']).R.mean().unstack(['any', 'half']).round(3).to_string())
print('\nEA別'); print(T.groupby(['ea', 'any', 'half']).R.mean().unstack(['any', 'half']).round(3).to_string())
