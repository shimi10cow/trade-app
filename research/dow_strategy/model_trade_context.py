import json,glob,bisect,sys,pandas as pd,numpy as np
sys.path.insert(0,'.')
from env_recognition.data import load
from env_recognition.ea_api import EnvRecognizer,TF_LEN
from env_recognition import dow_trend
from env_recognition.pivots import pivot_events,atr
sys.path.insert(0,'dow_strategy')
from long_features import stage_arrays
S=str(__import__('pathlib').Path(__file__).with_name('feedback'))
M=[dict(json.load(open(f)),id=f.split('/')[-1][:-5]) for f in glob.glob(S+'/model_trades/*.json')]
D=[json.load(open(f)) for f in glob.glob(S+'/drawings/*.json')]
fr={tf:load(tf,'long') for tf in ('D1','H4','H1')}
fr={tf:df[pd.to_datetime(df.t)>='2024-01-01'].reset_index(drop=True) for tf,df in fr.items()}
env=EnvRecognizer(fr)
st4=stage_arrays(env.tf['H4']['res'],len(env.tf['H4']['df']));st1=stage_arrays(env.tf['H1']['res'],len(env.tf['H1']['df']))
m15=load('M15','long');m15=m15[pd.to_datetime(m15.t)>='2025-10-01'].reset_index(drop=True)
r15=dow_trend.run(m15,'M15');T15=list(pd.to_datetime(m15.t)+TF_LEN['M15'])
c=m15.c;ll=m15.l.rolling(14).min();hh=m15.h.rolling(14).max();K=(100*(c-ll)/(hh-ll)).rolling(3).mean();Dd=K.rolling(5).mean()
sma=lambda df,n:df.c.rolling(n).mean()
h1=env.tf['H1']['df'];s20,s75=sma(h1,20),sma(h1,75);H1C=list(pd.to_datetime(h1.t)+TF_LEN['H1'])
a4=atr(env.tf['H4']['df'])
P15=sorted(((T15[e['available_idx']],e['kind'],e['price']) for e in pivot_events(m15)),key=lambda x:x[0])
H1P=sorted(((pd.Timestamp(h1.t[e['available_idx']])+TF_LEN['H1'],e['kind'],e['price']) for e in env.tf['H1']['res']['pivot_events']),key=lambda x:x[0])
EA=pd.read_csv('dow_strategy/results/long_features_1.csv',parse_dates=['time']);EA=EA[EA.time>='2026-01-01']
def lastsw(P,ts,kind,side,entry):
    for t,k,p in reversed(P[:bisect.bisect_right([x[0] for x in P],ts)]):
        if k==kind and ((p<entry) if side==1 else (p>entry)):return p
rows=[]
for m in sorted(M,key=lambda x:x['t']):
    t=pd.Timestamp(m['t'],unit='s');side=m['side'];d='up' if side==1 else 'down';en=m['p'];sl=m['sl']['p']
    s=env.state_at(t);k4=env.last_closed('H4',t);k1=env.last_closed('H1',t);i15=bisect.bisect_right(T15,t)-1
    kind='lo' if side==1 else 'hi'
    sw15=lastsw(P15,t,kind,side,en);sw1=lastsw(H1P,t,kind,side,en)
    ea=EA[(EA.side==side)&((EA.time-t).abs()<=pd.Timedelta(hours=24))]
    rows.append(dict(t=t,k=m.get('kind','real')[0],side=side,R=round((m['exit']['p']-en)*side/abs(en-sl),2),
      D1=s['D1']['trend']==d,H4=s['H4']['trend']==d,H4stg=int(st4[k4]) if s['H4']['trend']==d else -1,
      H1=s['H1']['trend']==d,H1stg=int(st1[k1]) if s['H1']['trend']==d else -1,M15=r15['bars'][i15][0]==d,M15prov=r15['prov_bars'][i15][0]==d,
      ma20_75=bool(side*(s20[k1]-s75[k1])>0),K=round(K[i15]),
      H4dist=round(side*(en-s['H4']['protected'])/a4[k4],1) if s['H4']['trend']==d else None,
      sl_pips=round(abs(en-sl)/1e-4,1),sl_vs_m15=round((sl-sw15)*side/1e-4,1) if sw15 else None,sl_vs_h1=round((sl-sw1)*side/1e-4,1) if sw1 else None,
      EA24h=len(ea)))
R=pd.DataFrame(rows);pd.set_option('display.width',250);print(R.to_string(index=False))
r=R[R.k=='r'];print('\nreal n',len(r),'sumR',r.R.sum().round(2),'win',(r.R>0).mean().round(2))
for c_ in ['D1','H4','H1','M15','M15prov','ma20_75']:print(c_,R[c_].mean().round(2))
print('H4stg',R.H4stg.value_counts().to_dict(),'H1stg',R.H1stg.value_counts().to_dict())
print('EA trade within 24h same side:',(R.EA24h>0).sum(),'/',len(R),'| EA 2026 trades',len(EA),'sumR',EA.Rc.sum().round(1))
