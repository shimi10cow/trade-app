"""Same engine, but the stochastic is computed on H1 bars (14,3,5) and seen on M15 as the last closed H1 value, so the
20/80 sequence completes once per H1 close; entry at the first M15 close after that H1 bar."""
import sys, os, copy, numpy as np, pandas as pd
exec(open('/home/user/trendlab/sx/run.py').read().split("CONF={")[0])
_bf=EM.build_features
def bf(pair,cfg=EM.CFG):
    m,h1,h4,h1p,m15p=_bf(pair,cfg)
    ll=h1.low.rolling(cfg.stoch_n).min(); hh=h1.high.rolling(cfg.stoch_n).max(); rk=100*(h1.close-ll)/(hh-ll)
    h1=h1.copy(); h1['K1']=rk.rolling(cfg.stoch_k).mean(); h1['D1']=h1.K1.rolling(cfg.stoch_d).mean()
    x=pd.merge_asof(m[['time']].sort_values('time'),h1[['avail_time','K1','D1']].sort_values('avail_time'),left_on='time',right_on='avail_time',direction='backward')
    m=m.copy(); m['K']=x.K1.to_numpy(); m['D']=x.D1.to_numpy()
    return m,h1,h4,h1p,m15p
EM.build_features=bf
sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import pivot_events
_h1=h1.reset_index().rename(columns=dict(open='o',high='h',low='l',close='c'))
_ev=pivot_events(_h1[['o','h','l','c']]); _Ch=(h1.index+pd.Timedelta('1h')).to_numpy()
_P={k:sorted((_Ch[e['available_idx']],e['price']) for e in _ev if e['action']=='confirm' and e['kind']==k) for k in ('hi','lo')}
_PT={k:np.array([a for a,_ in v]) for k,v in _P.items()}
def swing_sl(t,side,entry,default):
    k='lo' if side==1 else 'hi'; j=np.searchsorted(_PT[k],np.datetime64(pd.Timestamp(t)),side='right')-1
    a=a1.iloc[max(0,np.searchsorted(C1,np.datetime64(pd.Timestamp(t)),side='right')-1)]
    while j>=0:
        p=_P[k][j][1]
        if (entry-p)*side>0.3*a: return p-side*0.2*a
        j-=1
    return None
kw={'h1new-H1山谷損切り':dict(extra_filter=newf,sl_fn=swing_sl),'h1orig':{},'h1new':dict(extra_filter=newf),'h1new-P1〜3':dict(extra_filter=newf,max_entry_point=3)}[conf]
cfg=copy.deepcopy(EM.CFG)
for k,v in kw.items(): setattr(cfg,k,v)
tr=pd.DataFrame(EM.run_pair(sym,cfg)); tr['sym']=sym; tr['conf']=conf
tr.to_pickle(f"/home/user/trendlab/sx/t_{sym}_{conf}.pkl"); print('done',sym,conf,len(tr),flush=True)
