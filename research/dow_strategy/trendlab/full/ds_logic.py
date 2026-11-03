import sys; sys.path.insert(0,'/home/user/trade-app'); sys.path.insert(0,'/home/user/trade-app/research')
import pandas as pd, numpy as np, pickle
from mt5_ea.live import engine as E
from mt5_ea.live.eas import ds as DS
COST={'JP225':3e-4,'US500':2e-4}
for sym in ('JP225','US500'):
    F=pickle.load(open(f'live_frames_{sym}.pkl','rb')); a=DS.ADOPTED[sym]
    evs=DS.setups(F,'H1'); LN={e['t']:e['ln_h'] for e in evs}
    base=[dict(e,ref=e['ref_H']) for e in evs]
    V={'2Rで利確（今）':(dict(exit='h1',act=99,tp=2.0),None),
       'ネックで利確':(dict(exit='h1',act=99,tp_px=True),'neck'),
       '値幅の目安で利確':(dict(exit='h1',act=99,tp_px=True),'mm'),
       '+1RからH1で追う':(dict(exit='h1',act=1.0),None),
       'ネックを抜けたらH1で追う':(dict(exit='h1',act=0.0),'neckgate')}
    print(f'\n== DS@{sym}')
    for lab,(ex,tpk) in V.items():
        cfg=dict(trig='all',stop='ref',buf=0.3,win=0.3,one_per_side=True,**ex)
        ev=[]
        for e in base:
            x=dict(e)
            if tpk=='neck': x['tp_px']=e['neck']
            elif tpk=='mm': x['tp_px']=e['neck']+e['side']*abs(e['ref_H']-e['neck'])
            ev.append(x)
        r=E.run(F,ev,cfg,entry_bar=True); tr=r['trades']
        if tpk=='neckgate': pass
        ok=lambda t,s,u: DS.adopted_filter(dict(tag=t,side=s),a['side'],LN.get(u) if a.get('ln') else None)
        tr=tr[[ok(t,s,u) for t,s,u in zip(tr.tag,tr.side,tr.setup_t)]].reset_index(drop=True)
        tr['R']=tr.R+F.COST/tr.risk-COST[sym]/tr.risk
        hv=np.where(pd.to_datetime(tr.t)<pd.Timestamp('2021-10'),1,2); r_=tr.R.to_numpy(); e_=np.cumsum(r_); dd=(e_-np.maximum.accumulate(np.r_[0,e_])[1:]).min()
        hold=(pd.to_datetime(tr.exit_t)-pd.to_datetime(tr.t)).dt.total_seconds().median()/86400
        print(f'  {lab:14s} {len(r_)}回 勝率 {(r_>0).mean():.0%} 平均 {r_.mean():+.2f} 前半 {r_[hv==1].mean():+.2f} 後半 {r_[hv==2].mean():+.2f} 合計 {r_.sum():+.1f} PF {r_[r_>0].sum()/-r_[r_<0].sum():.2f} DD {dd:.1f} 保有 {hold:.1f}日 勝ちの中央 {np.median(r_[r_>0]):+.2f}R')
