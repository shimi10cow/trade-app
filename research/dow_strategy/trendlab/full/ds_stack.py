import sys; sys.path.insert(0,'/home/user/trade-app'); sys.path.insert(0,'/home/user/trade-app/research')
import pandas as pd, numpy as np, pickle
from mt5_ea.live import engine as E
from mt5_ea.live.eas import ds as DS
from mt5_ea.live.eas.nt import h4_shape
COST={'JP225':3e-4,'US500':2e-4}; OUT={}
V={'A 2R利確・1つまで（今）':dict(exit='h1',act=99,tp=2.0,one_per_side=True),
   'B H1で追う(+1R)・1つまで':dict(exit='h1',act=1.0,one_per_side=True),
   'C H1で追う(+1R)・2つまで':dict(exit='h1',act=1.0,one_per_side=False,max_side=2),
   'D H1で追う(+1R)・2つ目は1つ目が+1R後':dict(exit='h1',act=1.0,stack=2),
   'E H1で追う(+1.5R)・2つ目は1つ目が+1.5R後':dict(exit='h1',act=1.5,stack=2),
   'F 2R利確・2つまで':dict(exit='h1',act=99,tp=2.0,one_per_side=False,max_side=2)}
for sym in ('JP225','US500'):
    F=pickle.load(open(f'live_frames_{sym}.pkl','rb')); a=DS.ADOPTED[sym]
    evs=DS.setups(F,'H1'); LN={e['t']:e['ln_h'] for e in evs}; base=[dict(e,ref=e['ref_H']) for e in evs]; sh=h4_shape(F.m15_all)
    print(f'\n== DS@{sym}')
    for lab,ex in V.items():
        cfg=dict(trig='all',stop='ref',buf=0.3,win=0.3,**ex)
        tr=E.run(F,base,cfg,entry_bar=True)['trades']
        ok=lambda t,s,u: DS.adopted_filter(dict(tag=t,side=s),a['side'],LN.get(u) if a.get('ln') else None)
        tr=tr[[ok(t,s,u) for t,s,u in zip(tr.tag,tr.side,tr.setup_t)]].reset_index(drop=True)
        if sym=='JP225': tr=tr[[sh(t,s)[0]<2.5 for t,s in zip(tr.t,tr.side)]].reset_index(drop=True)
        tr['R']=tr.R+F.COST/tr.risk-COST[sym]/tr.risk; OUT[(sym,lab)]=tr
        hv=np.where(pd.to_datetime(tr.t)<pd.Timestamp('2021-10'),1,2); r=tr.sort_values('t').R.to_numpy(); e=np.cumsum(r); dd=(e-np.maximum.accumulate(np.r_[0,e])[1:]).min(); s5=np.sort(r)[::-1]
        ls=mx=0
        for x in r: ls=ls+1 if x<0 else 0; mx=max(mx,ls)
        yrs=(pd.to_datetime(tr.exit_t).max()-pd.to_datetime(tr.t).min()).days/365.25
        print(f'  {lab:28s} {len(r)}回（年{len(r)/yrs:.1f}） 勝率 {(r>0).mean():.0%} 平均 {r.mean():+.2f} 前半 {tr.R[hv==1].mean():+.2f} 後半 {tr.R[hv==2].mean():+.2f} 合計 {r.sum():+.1f} PF {r[r>0].sum()/-r[r<0].sum():.2f} DD {dd:.1f} 連敗 {mx} 上位5 {s5[:5].sum()/r.sum():.0%}')
pd.to_pickle(OUT,'full/ds_stack.pkl')
