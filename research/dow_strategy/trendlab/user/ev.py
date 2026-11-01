"""User's own entry places, judged only by 'did it extend': H4 出入口 (broken protected after an H4 turn), H4 砦 (current protected),
D1/H4 impulse trendline touch (EA-L line, 3rd-4th touch). Causal: H4/D1 state as of the last closed bar."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from env_recognition import dow_trend
from env_recognition.pivots import atr
import importlib; L=importlib.import_module('mt5_ea.live.eas.l'); L.ULOOK['D1']=20
LOG={'XAUUSD','XAGUSD','US500','JP225'}
def rs(h,rule): return h.set_index('t').resample(rule,label='left',closed='left').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index()
def run(sym):
    h=pd.read_pickle(f'/home/user/trendlab/h1_{sym}.pkl')[['t','o','h','l','c']].reset_index(drop=True)
    if sym in LOG:
        for z in 'ohlc': h[z]=np.log(h[z])
    h=h[h.t>='2005-01-01'].reset_index(drop=True)
    h4=rs(h,'4h'); d1=rs(h,'1D'); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
    R4=dow_trend.run(h4,'H4'); RD=dow_trend.run(d1,'D1')
    A4=atr(h4); AD=atr(d1); A1=pd.Series(atr(h)).rolling(500,min_periods=50).mean().to_numpy()
    C4=h4.t+pd.Timedelta('4h'); CD=d1.t+pd.Timedelta('1D'); T1=h.t; C1=T1+pd.Timedelta('1h')
    c1=h.c.to_numpy(); hi1=h.h.to_numpy(); lo1=h.l.to_numpy(); n=len(c1)
    sma=pd.Series(h4.c).rolling(1200).mean().to_numpy()
    bars4=R4['bars']; barsD=RD['bars']
    def i1_at(t): return int(C1.searchsorted(t))      # first H1 bar closing at/after t
    def ctx(i,s):
        t=C1[i]; k=int(C4.searchsorted(t,side='right'))-1; kd=int(CD.searchsorted(t,side='right'))-1
        f=dict(dside=float(s*(h4.c.iat[k]-sma[k])>0) if not np.isnan(sma[k]) else np.nan,
               h4=float(bars4[k][0]==('up' if s==1 else 'down')), d1=float(barsD[kd][0]==('up' if s==1 else 'down')) if kd>=0 else np.nan)
        for H in (24,72,240): f[f'f{H}']=s*(c1[min(n-1,i+H)]-c1[i])/A1[i] if i+H<n else np.nan
        e=min(n,i+241); f['mfe']=((hi1[i+1:e].max()-c1[i]) if s==1 else (c1[i]-lo1[i+1:e].min()))/A1[i]; f['mae']=((c1[i]-lo1[i+1:e].min()) if s==1 else (hi1[i+1:e].max()-c1[i]))/A1[i]
        return f
    out=[]
    # 出入口 / 砦 on H4 state, touched by H1 bars
    rev=[e for e in R4['events'] if e.get('machine')=='major' and e['action']=='REVERSAL']
    for e in rev:
        k=e['idx']; s=1 if e['to']=='up' else -1; G=e['broken_price']; a=A4[k]
        k2=k+1
        while k2<len(bars4) and bars4[k2][0]==e['to']: k2+=1
        i=i1_at(C4[k]); iend=i1_at(C4[min(k2,len(C4)-1)])
        for j in range(i,min(iend,n-1)):
            if (lo1[j]<=G+0.3*a and c1[j]>=G-1.0*a) if s==1 else (hi1[j]>=G-0.3*a and c1[j]<=G+1.0*a):
                out.append(dict(sym=sym,kind='出入口',t=C1[j],s=s,wait=j-i,**ctx(j,s))); break
    # 砦: each new protected value while trend holds
    seen=set()
    for k in range(1,len(bars4)-1):
        tr,P=bars4[k]
        if tr not in('up','down') or P is None or (tr,P) in seen: continue
        seen.add((tr,P)); s=1 if tr=='up' else -1; a=A4[k]
        k2=k+1
        while k2<len(bars4) and bars4[k2]==(tr,P): k2+=1
        i=i1_at(C4[k]); iend=i1_at(C4[min(k2,len(C4)-1)])
        for j in range(i,min(iend,n-1)):
            if (lo1[j]<=P+0.3*a and c1[j]>P) if s==1 else (hi1[j]>=P-0.3*a and c1[j]<P):
                out.append(dict(sym=sym,kind='砦',t=C1[j],s=s,wait=j-i,**ctx(j,s))); break
    # trendline touches (EA-L line rules), H4 and D1
    for tf,df,R,C,A in (('H4',h4,R4,list(C4),A4),('D1',d1,RD,list(CD),AD)):
        for e in L.line_touches(df,R,C,A,tf):
            if e['kind']!='touch' or not(3<=e['n']<=4) or e['trend']!=e['d']: continue
            if e['angle']<0.03 or e['depth'] is None or not(0.3<=e['depth']<=0.85): continue
            j=i1_at(e['t']); s=1 if e['d']=='up' else -1
            if j<n-1: out.append(dict(sym=sym,kind='TL'+tf,t=C1[j],s=s,wait=0,**ctx(j,s)))
    # baseline: every 5th H1 bar, H4 trend direction
    for j in range(2000,n-241,5):
        k=int(C4.searchsorted(C1[j],side='right'))-1; tr=bars4[k][0]
        if tr in('up','down'): s=1 if tr=='up' else -1; out.append(dict(sym=sym,kind='基準H4向き',t=C1[j],s=s,wait=0,**ctx(j,s)))
    return pd.DataFrame(out)
if __name__=='__main__':
    sym=sys.argv[1]; run(sym).to_pickle(f'/home/user/trendlab/user/ev_{sym}.pkl'); print('done',sym)
