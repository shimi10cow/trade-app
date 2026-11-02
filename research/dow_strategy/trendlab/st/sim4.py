"""Round 4 (EURUSD / XAUUSD): pullback episodes. Within one H1 SMA20/75 regime, a pullback = the first M15 MA trigger (round 1 'MA')
after price has closed at least `away` ATR15 beyond the M15 SMA20 since the previous pullback. Number them 1, 2, 3...
Trade every numbered pullback that passes TR2 (context checked at the trigger). Stop k ATR15, exit after N hours. Max 2 open."""
import sys, numpy as np, pandas as pd
from sim import COST, SPLIT, build
from sim3 import run
rows=[]
for sym in ('EURUSD','XAUUSD'):
    f, ok, gap, ctx, trg = build(sym); n=len(f)
    c=f.c.to_numpy(); m20=f.m20.to_numpy(); a=f.a15.to_numpy()
    reg=np.sign(f.h1m20-f.h1m75).fillna(0).to_numpy()
    for away in (1.0,2.0):
        num=np.zeros(n,int); idx=[]; sd=[]
        cur=0; k=0; armed=False
        for i in range(1,n):
            if reg[i]!=cur: cur=reg[i]; k=0; armed=True
            if cur==0: continue
            if (c[i]-m20[i])*cur>=away*a[i]: armed=True
            if armed and trg[('MA',int(cur))][i]:
                k+=1; armed=False
                if ctx[('TR2',int(cur))][i] and ok[i]: idx.append(i); sd.append(int(cur)); num[i]=k
        idx=np.array(idx); sd=np.array(sd,dtype=np.int64)
        A={x:f[x].to_numpy(float) for x in ('o','h','l','c','m75','sh','sl','a15')}
        for kst in (3.0,4.0):
            st=A['c'][idx]-kst*A['a15'][idx]*sd
            for hrs in (16,24,48):
                oi,R,ox=run(idx,sd,st,A['o'],A['h'],A['l'],A['c'],A['m75'],A['sh'],A['sl'],gap,hrs*4,False,False,2)
                sel=oi>=0; en=A['o'][oi[sel]+1]; risk=(en-st[sel])*sd[sel]
                rows.append(pd.DataFrame(dict(sym=sym,away=away,stop=kst,hrs=hrs,t=f.time.to_numpy()[oi[sel]],side=sd[sel],num=num[oi[sel]],
                    R0=R[sel],cR=COST[sym]/risk,half=np.where(f.time.to_numpy()[oi[sel]]<np.datetime64(pd.Timestamp(SPLIT[sym])),1,2))))
d=pd.concat(rows,ignore_index=True); d['R']=d.R0-d.cR; d.to_pickle('r4.pkl')
d['nb']=pd.cut(d.num,[0,1,2,3,5,99],labels=['1','2','3','4-5','6+'])
for (aw,ks,hr),g in d.groupby(['away','stop','hrs']):
    t=g.groupby(['nb','sym','half']).R.mean().unstack(['sym','half']).round(2); t.columns=[f'{a[:3]}{b}' for a,b in t.columns]
    t['n/yr']=(g.groupby('nb').size()/21).round(0)
    print(f'\n== away {aw} stop {ks} {hr}h'); print(t.to_string())
