import sys, pandas as pd
sym = sys.argv[1]; sys.argv = ['run.py', sym]
exec(open('/home/user/trendlab/audit/run.py').read().split("E = {}")[0])
def full(r):
    tr = r['trades'].copy(); tc = [c for c in ('t', 'time', 'entry_t') if c in tr][0]
    tr['t'] = pd.to_datetime(tr[tc]); tr['exit_t'] = pd.to_datetime(tr['exit_t']); tr = tr[tr.t >= '2005-06-01']
    return tr[['t', 'exit_t', 'side', 'R']].assign(sym=sym)
out = {}
if sym == 'USDJPY':
    out['今'] = full(J2.run(F, **J2.ADOPTED['USDJPY'])); out['時間帯なし'] = full(J2.run(F, h1='h1major', hours=None))
if sym == 'US30':
    out['今'] = full(pgate(gate(lambda F_, e_: rt_run(), 'open'), 'band')(F, env))
    out['日足なし'] = full(pgate(gate(lambda F_, e_: rt_run(('side',)), 'open'), 'band')(F, env))
for k, v in out.items(): print(sym, k, len(v), round(v.R.mean(), 3), flush=True)
pd.to_pickle(out, f'/home/user/trendlab/audit/jt_{sym}.pkl')
