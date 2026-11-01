import pandas as pd, numpy as np
from lab import *
rows = []
for sym in DEV + OOS:
    h, d = load(sym); L = legs(d)
    for k in ('don', 'ma', 'dow'):
        r = eval_state(d, L, state(d, k)); r.update(sym=sym, kind=k, grp='作る側' if sym in DEV else '確かめる側', legs=len(L)); rows.append(r)
R = pd.DataFrame(rows); pd.set_option('display.width', 200)
print(R.groupby(['grp', 'kind'])[['found', 'lag', 'cover', 'precision']].mean().round(2).to_string())
print(R.groupby('sym').legs.first().to_dict())
R.to_pickle('state_eval.pkl')
