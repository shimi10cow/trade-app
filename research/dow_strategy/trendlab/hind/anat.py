import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import atr as atr7
from lab import load
X=pd.read_pickle('feat_box2.pkl'); out=[]
for sym,g in X.groupby('sym'):
    h,_=load(sym); h=h.reset_index(drop=True); hi,lo,c=(h[z].to_numpy(float) for z in 'hlc'); A=np.asarray(atr7(h)); T=pd.to_datetime(h.t)
    idx=T.searchsorted(g.t)
    for (k,r),i in zip(g.iterrows(),idx):
        s=r.s; en=c[i]; risk=r.risk*A[i]; sl=en-s*risk; n=len(c)
        e=min(n,i+241); fh=hi[i+1:e]; fl=lo[i+1:e]
        fav=(fh-en)*s/risk if s==1 else (en-fl)/risk; adv=(en-fl)/risk if s==1 else (fh-en)/risk
        hit=np.flatnonzero(adv>=1); stop=int(hit[0]) if len(hit) else 999
        t3=np.flatnonzero(fav>=3); tp=int(t3[0]) if len(t3) else 999
        mfe_pre=fav[:stop].max() if stop>0 and stop<999 else (fav.max() if stop==999 else 0)
        after3 = tp<999 and tp>stop and stop<999            # stopped, then +3R reached anyway (within 240 bars)
        # stop 1.5x / 2x: would it survive and reach 3R(original)?
        def surv(m):
            hs=np.flatnonzero(adv>=m); st=int(hs[0]) if len(hs) else 999; return tp<st
        out.append(dict(_k=k,stop_bar=stop,tp_bar=tp,win=tp<stop,mfe_pre=mfe_pre,after3=after3,s15=surv(1.5),s2=surv(2.0),mfe240=fav.max()))
X=X.join(pd.DataFrame(out).set_index('_k')); X.to_pickle('feat_anat.pkl'); print('done')
