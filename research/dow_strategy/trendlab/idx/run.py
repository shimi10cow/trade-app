"""Index / commodity CFDs (XM, 2016-10 ..): the intraday EAs that trade indices now (T, Q, DS, P) on new symbols."""
import sys, os, pickle, time, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app'); sys.path.insert(0,'/home/user/trade-app/research')
from mt5_ea.live.core import Frames
from mt5_ea.live.env import Env
from mt5_ea.live.eas import rt as RT, q as Q, ds as DS, nt as NT
from mt5_ea.live.eas.h4gate import gate
from mt5_ea.live.eas.pgate import gate as pgate
from mt5_ea.live import engine as E
sym=sys.argv[1]; t0=time.time()
COST={'US30':1.5e-4,'US500':2e-4,'US100':2e-4,'GER40':1.5e-4,'UK100':1.5e-4,'EU50':3e-4,'OIL':6e-4,'BRENT':6e-4,'NGAS':6e-3,'JP225':3e-4}[sym]
m=pd.read_pickle(f'/home/user/trendlab/idx/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
m['o'],m['h'],m['l'],m['c']=[np.round(m[k],6) for k in 'ohlc']
cache=f'/home/user/trendlab/idx/frames_{sym}.pkl'
if os.path.exists(cache): F=pickle.load(open(cache,'rb'))
else:
    F=Frames(m,'2017-07-01',h_days=10000,m_days=10000); pickle.dump(F,open(cache,'wb'))
env=Env(F.m15_all); print(sym,'frames',round(time.time()-t0),flush=True)
def ds_run(F,cfgname,side):
    evs=DS.setups(F,'H1'); LN={e['t']:e['ln_h'] for e in evs}
    r=DS.run_variant(F,'H1','left','h1s15',events=evs); tr=r['trades']
    if len(tr): tr=tr[[DS.adopted_filter(dict(tag=t,side=s),side,LN.get(u)) for t,s,u in zip(tr.tag,tr.side,tr.setup_t)]]
    return dict(trades=tr,open=[],pending=[])
NT.COST[sym]=COST
EAS={'T':pgate(gate(lambda F,e: RT.run(F,'T1t',env=e),'open'),'band'),
     'Q_us30':lambda F,e: Q.run(F,*Q.ADOPTED['US30']), 'Q_xag':lambda F,e: Q.run(F,*Q.ADOPTED['XAGUSD']), 'Q_xau':lambda F,e: Q.run(F,*Q.ADOPTED['XAUUSD']),
     'DS':gate(lambda F,e: ds_run(F,'JP225',None),'open'), 'DSbuy':lambda F,e: ds_run(F,'US500',1),
     'P':lambda F,e: NT.run(F,sym,seed=False)}
out=[]
for k,fn in EAS.items():
    try:
        r=fn(F,env); tr=pd.DataFrame(r['trades'])
        if not len(tr): print(k,0); continue
        tc=[c for c in ('t','time','entry_t') if c in tr][0]; ec=[c for c in ('exit_t','ExitTime') if c in tr][0]
        tr=tr.assign(t=pd.to_datetime(tr[tc]),exit_t=pd.to_datetime(tr[ec]))
        if 'open_end' in tr: tr=tr[~tr.open_end.fillna(False).astype(bool)]
        base_cost=NT.COST[sym] if k=='P' else (1.2e-4)
        R=tr.R+base_cost/tr.risk-COST/tr.risk
        out.append(pd.DataFrame(dict(key=f'{k}@{sym}',ea=k,sym=sym,t=tr.t,exit_t=tr.exit_t,side=tr.side.astype(int),R=R,risk=tr.risk)))
        print(sym,k,len(tr),round(R.sum(),1),round(time.time()-t0),flush=True)
    except Exception as ex:
        import traceback; traceback.print_exc()
pd.concat(out).to_pickle(f'/home/user/trendlab/idx/t_{sym}.pkl'); print('done',sym,flush=True)
