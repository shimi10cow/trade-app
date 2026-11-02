import pandas as pd, numpy as np, warnings, sys; warnings.filterwarnings('ignore')
sys.argv=[sys.argv[0]]; from sim import build
CFG='MA|A4|24h|T|p1'; out=[]
for s in ['EURUSD','XAUUSD']:
    d=pd.read_pickle(f'r3_{s}.pkl'); d=d[d.cfg==CFG].reset_index(drop=True)
    f,ok,gap,ctx,trg=build(s); n=len(f)
    reg=np.sign(f.h1m20-f.h1m75).fillna(0).to_numpy()
    chg=np.r_[True,reg[1:]!=reg[:-1]]; start=np.maximum.accumulate(np.where(chg,np.arange(n),0))
    age=(np.arange(n)-start)/4.0                     # hours since the H1 SMA20/75 regime began
    cnt={}
    for sd in (1,-1):
        t=(trg[('MA',sd)]&(reg==sd)).astype(int); cs=np.cumsum(t); cnt[sd]=cs-cs[start]+0   # MA touches since regime start (incl. this)
    hi16=f.h.rolling(16).max().to_numpy(); lo16=f.l.rolling(16).min().to_numpy()
    vol=(f.a15/f.a15.rolling(96*20).mean()).to_numpy()
    ix=pd.Index(f.time).get_indexer(d.t); sd=d.side.to_numpy()
    a=f.a15.to_numpy()[ix]
    d['age']=age[ix]; d['cnt']=np.where(sd==1,cnt[1][ix],cnt[-1][ix])
    d['depth']=np.where(sd==1,hi16[ix]-f.l.to_numpy()[ix],f.h.to_numpy()[ix]-lo16[ix])/a
    d['vol']=vol[ix]; d['hr']=d.t.dt.hour; d['op']=f.op4.to_numpy()[ix]*sd; d['h1sl']=f.h1sl.to_numpy()[ix]*sd
    d['er']=f.h1er.to_numpy()[ix]
    d['R']=d.R0-d.cR; out.append(d)
d=pd.concat(out,ignore_index=True); d.to_pickle('ev4.pkl')
print(d.groupby(['sym','half']).R.agg(['mean','count']).round(3))
print(d.groupby(['sym','side','half']).R.mean().unstack().round(3))
def show(col,bins=None):
    q=pd.cut(d[col],bins) if bins is not None else pd.qcut(d[col].rank(method='first'),5,labels=False)
    t=d.groupby([q,'sym','half']).R.agg(['mean','count']).unstack(['sym','half'])
    print('\n==',col); print(t['mean'].round(3).join(t['count'].sum(axis=1).rename('n')).to_string())
show('age',[0,6,12,24,48,96,1e9]); show('cnt',[0,1,2,3,5,1e9]); show('depth'); show('vol',[0,.6,.75,.9,1.1,1.4,9]); show('hr',[-1,2,5,8,11,14,17,20,23]); show('op'); show('h1sl'); show('er')
