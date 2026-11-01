"""User's hindsight-mark pattern as a rule: cross dir; pullback from the 20-bar extreme >= D ATR7, low pierces MA20 by >= P ATR;
turn bar (bull candle closing above prev high); enter at close; stop under pullback low - 0.3 ATR. Up to 3 per cross."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trendlab'); sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import pivot_events, atr as atr7
from lab import load, COST
from xlab import simulate
def run(sym, D=2.5, P=0.5, slope_min=0.0, spread_min=0.0, above75=True, maxk=3):
    h,_=load(sym); o,hi,lo,c=(h[z].to_numpy(float) for z in 'ohlc'); T=h.t.to_numpy(); A=np.asarray(atr7(h)); cost=COST[sym]
    m20=pd.Series(c).rolling(20).mean().to_numpy(); m75=pd.Series(c).rolling(75).mean().to_numpy(); up=m20>m75
    ev=sorted(pivot_events(h[['o','h','l','c']]),key=lambda e:e['available_idx']); conf={}
    for e in ev: conf.setdefault(e['available_idx'],[]).append(e)
    rows=[]; last_cross=0; k=0; used_low=-1
    for i in range(200,len(c)-2):
        if up[i]!=up[i-1]: last_cross=i; k=0; used_low=-1; continue
        if k>=maxk: continue
        s=1 if up[i] else -1
        w0=max(last_cross,i-20)
        if i-w0<3: continue
        seg_h=hi[w0:i+1] if s==1 else -lo[w0:i+1]
        ex=w0+int(np.argmax(seg_h)); ext=hi[ex] if s==1 else lo[ex]
        if ex>=i-1: continue
        pl=ex+int(np.argmin(lo[ex:i+1]) if s==1 else np.argmax(hi[ex:i+1])); pbx=lo[pl] if s==1 else hi[pl]
        if pl==used_low or pl<i-5: continue
        if (ext-pbx)*s < D*A[i]: continue
        if (pbx-m20[pl])*s > -P*A[i]: continue
        if above75 and (pbx-m75[pl])*s < 0: continue
        if (m75[i]-m75[i-10])*s/A[i] < slope_min or (m20[i]-m75[i])*s/A[i] < spread_min: continue
        turn=(c[i]>hi[i-1] and c[i]>o[i]) if s==1 else (c[i]<lo[i-1] and c[i]<o[i])
        if not turn: continue
        en=c[i]; sl=pbx-s*0.3*A[i]
        if (en-sl)*s<=0: continue
        k+=1; used_low=pl; cb=(m20<m75) if s==1 else (m20>m75)
        r=dict(sym=sym,t=T[i],s=s,k=k,since=i-last_cross,risk=(en-sl)*s/A[i])
        for kind in ('tp2','tp3','trail','ma'):
            R,_=simulate(o,hi,lo,c,A,conf,i,s,en,sl,cb,kind); r['R_'+kind]=R-cost/((en-sl)*s)
        rows.append(r)
    return pd.DataFrame(rows)
if __name__=='__main__':
    import itertools, pickle
    SY=['EURUSD','GBPUSD','AUDUSD','USDCAD','USDCHF','USDJPY','EURJPY','AUDJPY','CADJPY','CHFJPY','XAUUSD','US500','JP225','OIL','NGAS']
    cfg=dict(base=dict(), noP=dict(P=-9), D2=dict(D=2.0), D3=dict(D=3.0), slope=dict(slope_min=0.3, spread_min=1.5), no75=dict(above75=False))
    name=sys.argv[1]; out=pd.concat([run(s,**cfg[name]) for s in SY]); out.to_pickle(f'/home/user/trendlab/hind/rule_{name}.pkl'); print(name,len(out))
