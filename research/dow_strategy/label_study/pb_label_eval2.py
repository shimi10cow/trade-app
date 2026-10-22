"""User's pullback labels (USDJPY 2009 H1, 2012-13) vs mechanical recognition, and calibrating an automatic pullback counter."""
import json, numpy as np, pandas as pd
S='/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
D=pd.read_pickle(f'{S}/pbm_jpy_all.pkl').sort_values('t'); D['per']=np.where(D.dt.dt.year<=2010,'2009','2013')
m=pd.read_csv(f'{S}/jpy/USDJPY_M15_long_broker.csv',parse_dates=['time']).set_index('time').loc['2008-06-01':'2013-12-31']
def bars(rule):
    b=m.resample(rule,label='left',closed='left').agg(dict(open='first',high='max',low='min',close='last')).dropna()
    pc=b.close.shift(); tr=np.maximum(b.high-b.low,np.maximum((b.high-pc).abs(),(b.low-pc).abs())); b['atr']=tr.rolling(14).mean(); return b
BR={'H1':bars('1h'),'H4':bars('4h')}
TT={k:np.array([int(t.timestamp()) for t in v.index]) for k,v in BR.items()}
def seq(tf,per):
    x=D[(D.tf==tf)&(D.per==per)]; out=[]; side=0; n=0; on=False; legs=[]; bt=None
    for r in x.itertuples():
        if r.kind=='B':
            if on: legs.append(n)
            side=r.side; n=0; on=True; bt=r.t; out.append((r.t,'B',side,0,r.p,bt))
        elif r.kind=='R':
            if on: legs.append(n)
            on=False; out.append((r.t,'R',0,0,r.p,bt))
        elif on: n+=1; out.append((r.t,'N',side,n,r.p,bt))
    if on: legs.append(n)
    return pd.DataFrame(out,columns=['t','k','side','n','p','bt']),legs
print('### 1. トレンド1本あたりの押しの数')
for per in ('2009','2013'):
    for tf in ('H4','H1'):
        s,legs=seq(tf,per)
        if not legs: continue
        c=pd.Series(legs).value_counts().sort_index().to_dict()
        print(f'{per} {tf}: B {len(legs)} 本、押し {(s.k=="N").sum()} 個、1本あたり平均 {np.mean(legs):.1f}、分布 {c}')
# ---- calibration: count pullbacks from the user's B with a depth rule, compare to the user's numbers
def auto_count(tf,bt,side,t_eval,k_atr,f_leg):
    b=BR[tf]; T=TT[tf]; i0=np.searchsorted(T,bt); i1=np.searchsorted(T,t_eval,'right')
    H=b.high.values; L=b.low.values; A=b.atr.values
    ext=H[i0] if side==1 else L[i0]; base=L[i0] if side==1 else H[i0]; n=0; inpb=False
    for j in range(i0,min(i1,len(T))):
        if side==1:
            if H[j]>ext:
                ext=H[j]
                if inpb: inpb=False; base=pbl
            depth=ext-L[j]; leg=ext-base
        else:
            if L[j]<ext:
                ext=L[j]
                if inpb: inpb=False; base=pbl
            depth=H[j]-ext; leg=base-ext
        if not inpb and depth>=k_atr*A[j] and depth>=f_leg*max(leg,1e-9):
            inpb=True; n+=1; pbl=L[j] if side==1 else H[j]
        if inpb: pbl=min(pbl,L[j]) if side==1 else max(pbl,H[j])
    return n
print('\n### 2. 押しの数え方の調整（あなたの B から数えて、あなたの番号と一致する割合）')
grid=[(k,f) for k in (0.5,1,1.5,2,3,4) for f in (0,0.236,0.382,0.5)]
res={}
for tf in ('H4','H1'):
    rows=[]
    for per in ('2009','2013'):
        s,_=seq(tf,per); N=s[s.k=='N']
        for r in N.itertuples():
            ev=r.t+(6 if tf=='H1' else 3)*(3600 if tf=='H1' else 14400)
            rows.append((per,r.n,{g:auto_count(tf,r.bt,r.side,ev,*g) for g in grid}))
    out=[]
    for g in grid:
        a=[(min(n,4)==min(d[g],4)) for per,n,d in rows]; a09=[(min(n,4)==min(d[g],4)) for per,n,d in rows if per=='2009']; a13=[(min(n,4)==min(d[g],4)) for per,n,d in rows if per=='2013']
        out.append((g,np.mean(a),np.mean(a09) if a09 else np.nan,np.mean(a13) if a13 else np.nan))
    out.sort(key=lambda z:-z[1]); res[tf]=out
    print(tf,'（押し',len(rows),'個）上位：'); 
    for g,a,a1,a2 in out[:5]: print(f'  深さ ATR×{g[0]} かつ 直前の上げの{g[1]:.0%}以上 → 一致 {a:.0%}（2009 {a1:.0%}／2013 {a2:.0%}）')
    cur=[o for o in out if o[0]==(2,0)][0]; print(f'  参考：今の自動に近い ATR×2 → {cur[1]:.0%}')

print('\n### 3. 別の数え方（MA に触れたら1回、スイングの安値ができたら1回 など）')
for tf in ('H4','H1'):
    b=BR[tf]; c=b.close; b['s20']=c.rolling(20).mean(); b['s75']=c.rolling(75).mean()
def count2(tf,bt,side,t_eval,rule,par):
    b=BR[tf]; T=TT[tf]; i0=np.searchsorted(T,bt); i1=np.searchsorted(T,t_eval,'right')
    H=b.high.values; L=b.low.values; C=b.close.values; M=b['s20' if rule in ('t20','c20') else 's75'].values
    n=0; armed=True; ext=H[i0] if side==1 else L[i0]
    for j in range(i0+1,min(i1,len(T))):
        newx=(H[j]>ext) if side==1 else (L[j]<ext)
        if newx: ext=H[j] if side==1 else L[j]
        if rule in ('t20','t75'): hit=(L[j]<=M[j]) if side==1 else (H[j]>=M[j])
        elif rule=='c20': hit=(C[j]<M[j]) if side==1 else (C[j]>M[j])
        elif rule=='swing':   # a swing low/high: lowest of +-par bars, confirmed par bars later (only bars known by t_eval)
            k=j-par
            if k<=i0: continue
            w=L[max(i0,k-par):j+1] if side==1 else H[max(i0,k-par):j+1]
            hit=(L[k]==w.min()) if side==1 else (H[k]==w.max())
        if armed and hit: n+=1; armed=False
        if not armed and newx and not hit: armed=True
    return n
rules=[('t20',0),('c20',0),('t75',0),('swing',3),('swing',5),('swing',10)]
names={'t20':'SMA20 にヒゲで触れたら','c20':'SMA20 を終値で割ったら','t75':'SMA75 に触れたら','swing':'スイング安値（前後{}本）'}
for tf in ('H4','H1'):
    rows=[]
    for per in ('2009','2013'):
        s,_=seq(tf,per)
        for r in s[s.k=='N'].itertuples():
            ev=r.t+(6 if tf=='H1' else 3)*(3600 if tf=='H1' else 14400)
            rows.append((per,r.n,{g:count2(tf,r.bt,r.side,ev,*g) for g in rules}))
    for g in rules:
        a=np.mean([min(n,4)==min(d[g],4) for per,n,d in rows]); a1=np.mean([min(n,4)==min(d[g],4) for per,n,d in rows if per=='2009']); a2=np.mean([min(n,4)==min(d[g],4) for per,n,d in rows if per=='2013'])
        diff=np.mean([min(d[g],4)-min(n,4) for per,n,d in rows])
        print(f'{tf} {names[g[0]].format(g[1]):22s} 一致 {a:.0%}（2009 {a1:.0%}／2013 {a2:.0%}） 平均のズレ {diff:+.2f}回')
