import sys, json, numpy as np, pandas as pd, glob
sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import pivot_events
LOG={'XAUUSD','XAGUSD','US500','JP225'}
x=pd.concat([pd.read_pickle(f) for f in glob.glob('/home/user/trendlab/user/ev_*.pkl')]); x=x[x.kind!='基準H4向き'].copy(); x['t']=pd.to_datetime(x.t)
x=x[(x.t>='2012-01-01')&x.f240.notna()]
rng=np.random.default_rng(21); S=[]
for sym,g in x.groupby('sym'):
    for kind,k in (('出入口',2),('砦',2),('TLH4',1)):
        gg=g[g.kind==kind]; S.append(gg.sample(min(k,len(gg)),random_state=int(rng.integers(1e6))))
    gd=g[g.kind=='TLD1']
    if len(gd) and rng.random()<0.5: S.append(gd.sample(1,random_state=int(rng.integers(1e6))))
S=pd.concat(S).sample(frac=1,random_state=4).reset_index(drop=True)
def rs(h,rule): return h.set_index('t').resample(rule,label='left',closed='left').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index()
out=[];key=[];cache={}
for n,r in S.iterrows():
    if r.sym not in cache:
        h=pd.read_pickle(f'/home/user/trendlab/h1_{r.sym}.pkl')[['t','o','h','l','c']].reset_index(drop=True)
        h4=rs(h,'4h'); d1=rs(h,'1D'); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
        lg=lambda df: df.assign(**{z:np.log(df[z]) for z in 'ohlc'}) if r.sym in LOG else df
        cache[r.sym]=dict(h1=h,h4=h4,d1=d1,P4=pivot_events(lg(h4)),PD=pivot_events(lg(d1)))
    D=cache[r.sym]; t=r.t                             # t = close time of the H1 bar
    h1=D['h1']; i1=int((h1.t+pd.Timedelta('1h')).searchsorted(t)); 
    c1=h1.c; m20=c1.rolling(20).mean(); m75=c1.rolling(75).mean()
    def frame(df,L,end_close,P=None,span=None):
        C=df.t+span; k=int(C.searchsorted(end_close,side='right'))-1
        a=max(0,k-L+1); sl=df.iloc[a:k+1]
        piv=[]
        if P is not None:
            last={}
            for e in P:
                if e['available_idx']<=k: last[e['id']]=e
            for e in sorted(last.values(),key=lambda e:e['idx']):
                if e['idx']>=a: piv.append([e['idx']-a, float(df.h.iat[e['idx']] if e['kind']=='hi' else df.l.iat[e['idx']]), e['kind']=='hi'])
        return sl,piv,a,k
    px=float(c1.iat[i1]); dg=max(0,5-int(np.floor(np.log10(abs(px))))-1); q=lambda v:[round(float(z),dg) for z in v]
    sD,pD,_,_=frame(D['d1'],120,t,D['PD'],pd.Timedelta('1D'))
    s4,p4,_,_=frame(D['h4'],180,t,D['P4'],pd.Timedelta('4h'))
    a1=max(0,i1-199); s1=h1.iloc[a1:i1+1]
    for p in pD+p4: p[1]=round(p[1],dg)
    sid=f'd{n+1:03d}'
    out.append(dict(id=sid,sym=r.sym,s=int(r.s),d=dg,
        D=dict(o=q(sD.o),h=q(sD.h),l=q(sD.l),c=q(sD.c),p=pD,tt=[t_.strftime('%y/%m/%d') for t_ in sD.t]),
        H4=dict(o=q(s4.o),h=q(s4.h),l=q(s4.l),c=q(s4.c),p=p4,tt=[t_.strftime('%m/%d') for t_ in s4.t]),
        H1=dict(o=q(s1.o),h=q(s1.h),l=q(s1.l),c=q(s1.c),m20=q(m20.iloc[a1:i1+1].bfill()),m75=q(m75.iloc[a1:i1+1].bfill()),tt=[t_.strftime('%m/%d %H') for t_ in s1.t])))
    key.append(dict(id=sid,**{k:r[k] for k in ['sym','kind','t','s','dside','d1','h4','f24','f72','f240','mfe','mae']}))
pd.DataFrame(key).to_pickle('key.pkl')
open('data.js','w').write('const DATA='+json.dumps(out,separators=(',',':'))+';')
print(len(out), pd.DataFrame(key).kind.value_counts().to_dict())
