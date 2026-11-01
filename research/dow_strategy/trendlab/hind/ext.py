import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import pivot_events, atr as atr7
from lab import load
X=pd.read_pickle('feat_anat.pkl')
FX=['EURUSD','GBPUSD','AUDUSD','USDCAD','USDCHF','USDJPY','EURJPY','AUDJPY','CADJPY','CHFJPY']
C=pd.concat({p:np.log(load(p)[0].set_index('t').c) for p in FX},axis=1).sort_index().ffill()
CUR=['EUR','GBP','AUD','CAD','CHF','JPY','USD']
def strength(L, excl=None):
    R=C.diff(L); S={}
    for cu in CUR:
        cols=[(p, 1 if p[:3]==cu else -1) for p in FX if cu in (p[:3],p[3:]) and p!=excl] or [(p, 1 if p[:3]==cu else -1) for p in FX if cu in (p[:3],p[3:])]
        S[cu]=sum(R[p]*sg for p,sg in cols)/len(cols)
    return pd.DataFrame(S)
cache={}
def strg(L,excl):
    k=(L,excl)
    if k not in cache: cache[k]=strength(L,excl)
    return cache[k]
VS={'XAUUSD':('XAU','USD'),'US500':(None,'USD'),'JP225':(None,'JPY'),'OIL':(None,'USD'),'NGAS':(None,'USD')}
out=[]
for sym,g in X.groupby('sym'):
    h,d=load(sym); h=h.reset_index(drop=True); hi,lo,c=(h[z].to_numpy(float) for z in 'hlc'); A=np.asarray(atr7(h)); T=pd.to_datetime(h.t)
    idx=T.searchsorted(g.t)
    # daily levels known at prior day close
    D=d.copy(); D['pdh']=D.h; D['pdl']=D.l
    W=d.resample('W-FRI').agg(dict(h='max',l='min'))
    dev=sorted(pivot_events(d[['o','h','l','c']].reset_index(drop=True)),key=lambda e:e['available_idx'])
    dt=d.index
    if sym in FX: base,quote=sym[:3],sym[3:]
    else: base,quote=VS[sym]
    for (k,r),i in zip(g.iterrows(),idx):
        s=r.s; t=r.t; en=c[i]; risk=r.risk*A[i]; f={'_k':k}
        for L in (24,72,240):
            S=strg(L,sym if sym in FX else None); j=S.index.searchsorted(t,side='right')-1
            if j<0: continue
            row=S.iloc[j]
            if sym in FX:
                f[f'cs{L}']=s*(row[base]-row[quote])/(A[i]/en)   # in ATR units (log ret / ATR fraction)
                f[f'b{L}']=s*row[base]/(A[i]/en); f[f'q{L}']=-s*row[quote]/(A[i]/en)
            else:
                f[f'q{L}']=-s*row[quote]/(A[i]/en) if sym!='US500' and sym!='OIL' and sym!='NGAS' else np.nan
        # levels
        jd=dt.searchsorted(t.floor('D'))-1
        if jd>=20:
            prev=d.iloc[jd]; lv_up=[prev.h, d.h.iloc[jd-19:jd+1].max()]; lv_dn=[prev.l, d.l.iloc[jd-19:jd+1].min()]
            jw=W.index.searchsorted(t.floor('D'))-1
            if jw>=0: lv_up.append(W.h.iloc[jw]); lv_dn.append(W.l.iloc[jw])
            sw=[e for e in dev if e['available_idx']<=jd]
            lv_up+= [e['price'] for e in sw[-8:] if e['kind']=='hi']; lv_dn+=[e['price'] for e in sw[-8:] if e['kind']=='lo']
            lv=np.array(lv_up+lv_dn)
            ahead=lv[(lv-en)*s>0]; behind=lv[(lv-en)*s<=0]
            f['room']=(np.min((ahead-en)*s)/risk) if len(ahead) else 20.0
            f['room_atrD']=(np.min((ahead-en)*s)/d.atr.iloc[jd]) if len(ahead) else 10.0
            f['back']=(np.min((en-behind)*s)/risk) if len(behind) else 20.0   # just broke a level? small = level right behind
            f['open_sky']=float(len(ahead)==0)
            f['pdr_pos']=((en-prev.l)/(prev.h-prev.l)) if s==1 else ((prev.h-en)/(prev.h-prev.l))
        out.append(f)
X=X.join(pd.DataFrame(out).set_index('_k')); X.to_pickle('feat_ext.pkl'); print('done',len(X))
