"""Does the Dow state machine converge when started later (window start), and how long does it take?"""
import time, sys, numpy as np, pandas as pd
sys.path.insert(0, '/home/user/trade-app/research')
from env_recognition import dow_trend
S = '/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
m = pd.read_csv(f'{S}/EURUSD_M15_long_broker.csv', parse_dates=['time']).rename(columns=dict(time='t', open='o', high='h', low='l', close='c'))
for tf, rule in (('H1', '1h'), ('H4', '4h'), ('M15', None)):
    d = m if rule is None else m.set_index('t').resample(rule, label='left', closed='left').agg(dict(o='first', h='max', l='min', c='last')).dropna().reset_index()
    d = d.iloc[-60000:].reset_index(drop=True) if tf == 'M15' else d
    t0 = time.time(); full = dow_trend.run(d, tf); tf_full = time.time() - t0
    fb = np.array([b[0] for b in full['bars']]); pb = np.array([b[0] for b in full['prov_bars']])
    for off in (len(d) - 6000, len(d) - 3000, len(d) - 1500):
        w = d.iloc[off:].reset_index(drop=True)
        t0 = time.time(); r = dow_trend.run(w, tf); tw = time.time() - t0
        wb = np.array([b[0] for b in r['bars']]); wp = np.array([b[0] for b in r['prov_bars']])
        same = fb[off:] == wb; samep = pb[off:] == wp
        first = np.argmax(np.cumprod(same[::-1])[::-1] == 1) if same[-1] else None  # first index after which all agree
        print(f'{tf} window {len(w)} bars: run {tw:.1f}s (full {len(d)} bars {tf_full:.1f}s) | agree after warm-up: major {same[len(w)//3:].mean():.4f} prov {samep[len(w)//3:].mean():.4f} | all-agree from bar {first}', flush=True)
