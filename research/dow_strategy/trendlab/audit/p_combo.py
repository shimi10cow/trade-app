import sys, pickle, pandas as pd
sys.path.insert(0, '/home/user/trendlab/audit')
sym = sys.argv[1]
sys.argv = ['run.py', sym]
src = open('/home/user/trendlab/audit/run.py').read().split("E = {}")[0]
exec(src)
out = {}
for lab, no in (('今', ()), ('勢いなし', ('imp',)), ('水平線なし', ('band',)), ('勢い・水平線なし', ('imp', 'band'))):
    r = nt_run(no); tr = r['trades'].copy(); tr['t'] = pd.to_datetime(tr.t); tr = tr[tr.t >= '2005-06-01']
    out[lab] = tr[['t', 'exit_t', 'side', 'R']].assign(sym=sym); print(sym, lab, len(tr), round(tr.R.mean(), 3), flush=True)
pd.to_pickle(out, f'/home/user/trendlab/audit/p_{sym}.pkl')
