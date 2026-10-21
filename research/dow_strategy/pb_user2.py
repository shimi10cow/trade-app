import sys, bisect, pandas as pd, numpy as np
sys.path.insert(0, '.')
from env_recognition.data import load
from env_recognition import dow_trend
from env_recognition.ea_api import TF_LEN
sys.path.insert(0, 'dow_strategy'); from gen_pbcount import Pushes
M = pd.read_pickle(sys.argv[1]); M = M[M.pb.notna()]
import os
TFX=os.environ.get('TFX','H1')
df = load(TFX, 'long').reset_index(drop=True); R = dow_trend.run(df, TFX)
ts = ((pd.to_datetime(df.t) + TF_LEN[TFX] - pd.Timestamp(0)) // pd.Timedelta(seconds=1)).tolist()
h, l = df.h.to_numpy(float), df.l.to_numpy(float)
conf = {}
for e in R['pivot_events']:
    if e['action'] == 'confirm': conf.setdefault(e['available_idx'], []).append(e)
for name, sides in [('prov', [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['prov_bars']]),
                    ('major', [1 if b[0] == 'up' else -1 if b[0] == 'down' else 0 for b in R['bars']])]:
    P = Pushes(); st = [P.step(i, sides[i], h[i], l[i], conf.get(i, [])) for i in range(len(df))]
    out = []
    for m in M.itertuples():
        j = bisect.bisect_right(ts, m.t + 3600) - 1; s, n = st[j]
        out.append('bo' if s != m.side else str(min(n + 1, 4)))
    M[name] = out
    print(name, '一致', (M[name] == M.pb).sum(), '/', len(M))
M[['dt','pb','prov','major']].to_csv('pbu_'+TFX+'.csv')
print(M[['dt', 'side', 'pb', 'pb_h1', 'pb_h1_dow', 'prov', 'major']].to_string(index=False))
