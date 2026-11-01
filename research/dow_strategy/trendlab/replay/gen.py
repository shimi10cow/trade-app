import sys, json, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import pivot_events
LOG={'XAUUSD','US500','JP225'}
SY=['EURUSD','GBPUSD','AUDUSD','USDCAD','USDCHF','USDJPY','EURJPY','AUDJPY','CADJPY','CHFJPY','XAUUSD','US500','JP225','OIL','NGAS']
def rs(h,rule): return h.set_index('t').resample(rule,label='left',closed='left').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index()
rng=np.random.default_rng(33); out=[]; key=[]
PRE,STEPS=200,480          # visible history at start, H1 bars to step through (~4 weeks)
for n,sym in enumerate(rng.permutation(SY)):
    h=pd.read_pickle(f'/home/user/trendlab/h1_{sym}.pkl')[['t','o','h','l','c']].reset_index(drop=True)
    h4=rs(h,'4h'); d1=rs(h,'1D'); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
    lg=lambda df: df.assign(**{z:np.log(df[z]) for z in 'ohlc'}) if sym in LOG else df
    lo_i=int(h.t.searchsorted(pd.Timestamp('2012-01-01'))); lo_i=max(lo_i,3000)
    s0=int(rng.integers(lo_i,len(h)-PRE-STEPS-300))
    a=s0-75; b=s0+PRE+STEPS                                   # H1 slice (75 warm-up for MA75)
    H=h.iloc[a:b].reset_index(drop=True); base=H.t.iat[0]
    hrs=lambda ts:((ts-base)/pd.Timedelta('1h')).astype(int)
    H1close=hrs(H.t+pd.Timedelta('1h'))
    def tf(df,span,back):
        C=df.t+span; k1=int(C.searchsorted(H.t.iat[-1]+pd.Timedelta('1h'),side='right'))
        k0=max(0,int(C.searchsorted(H.t.iat[75+PRE-1]+pd.Timedelta('1h'),side='right'))-back)
        sl=df.iloc[k0:k1].reset_index(drop=True)
        ev=[]
        for e in pivot_events(lg(df)):
            if k0<=e['idx']<k1 and e['available_idx']<k1:
                price=float(df.h.iat[e['idx']] if e['kind']=='hi' else df.l.iat[e['idx']])
                ev.append([e['id'],e['idx']-k0,price,e['kind']=='hi',int(hrs(pd.Series([C.iat[e['available_idx']]])).iat[0])])
        return sl,list(hrs(C.iloc[k0:k1])),ev
    s4,c4,e4=tf(h4,pd.Timedelta('4h'),150); sD,cD,eD=tf(d1,pd.Timedelta('1D'),100)
    px=float(H.c.iat[-1]); dg=max(0,5-int(np.floor(np.log10(abs(px))))-1); q=lambda v:[round(float(z),dg) for z in v]
    for e in e4+eD: e[2]=round(e[2],dg)
    wid=f'r{n+1:02d}'
    out.append(dict(id=wid,sym=sym,d=dg,start=75+PRE-1,
        H1=dict(o=q(H.o),h=q(H.h),l=q(H.l),c=q(H.c),cl=list(H1close),tt=[t.strftime('%m/%d %H') for t in H.t]),
        H4=dict(o=q(s4.o),h=q(s4.h),l=q(s4.l),c=q(s4.c),cl=c4,tt=[t.strftime('%m/%d') for t in s4.t],ev=e4),
        D=dict(o=q(sD.o),h=q(sD.h),l=q(sD.l),c=q(sD.c),cl=cD,tt=[t.strftime('%y/%m/%d') for t in sD.t],ev=eD)))
    key.append(dict(id=wid,sym=sym,a=a,t0=H.t.iat[0]))
pd.DataFrame(key).to_pickle('key.pkl')
open('data.js','w').write('const DATA='+json.dumps(out,separators=(',',':'))+';')
print(len(out)); import os; print(os.path.getsize('data.js'))
