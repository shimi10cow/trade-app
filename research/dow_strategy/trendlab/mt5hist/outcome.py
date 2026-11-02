import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research')
from env_recognition.pivots import pivot_events, atr
T=pd.read_pickle('trades_mt5.pkl'); out=[]
for sym,g in T.groupby('symbol'):
    try: b=pd.read_csv(f'bars_{sym}.csv.gz')
    except FileNotFoundError: continue
    b['t']=pd.to_datetime(b.time); b=b.rename(columns=dict(open='o',high='h',low='l',close='c')).reset_index(drop=True)
    ev=pivot_events(b[['o','h','l','c']]); A=atr(b)
    P=sorted((e['available_idx'],e['kind'],e['price']) for e in ev if e['action']=='confirm')
    PA=[p[0] for p in P]; h,l,c=b.h.to_numpy(),b.l.to_numpy(),b.c.to_numpy(); n=len(c)
    import bisect
    for _,r in g.iterrows():
        i=int(b.t.searchsorted(r.t_in.floor('15min')))       # bar containing the first entry
        if i<50 or i>=n-2: continue
        s=r.s; en=r.px_in
        if pd.notna(r.sl): sl=r.sl; src='MT5'
        else:
            k=bisect.bisect_right(PA,i-1)-1; sl=None
            while k>=0:
                if P[k][1]==('lo' if s==1 else 'hi') and (en-P[k][2])*s>0.3*A[i]: sl=P[k][2]-s*0.1*A[i]; break
                k-=1
            src='M15山谷'
        if sl is None: continue
        risk=(en-sl)*s
        E=min(n,i+960); fav=((h[i:E]-en) if s==1 else (en-l[i:E]))/risk; adv=((en-l[i:E]) if s==1 else (h[i:E]-en))/risk
        st=np.flatnonzero(adv>=1); js=st[0] if len(st) else len(fav)
        f=dict(tid=r.tid,symbol=sym,s=s,tj=r.tj_in,matched=r.matched,eid=r.eid,sl_src=src,risk_atr=risk/A[i],
               R=(r.px_out-en)*s/risk if pd.notna(r.px_out) else np.nan, hold_h=r.hold_h, mfe=fav[:js].max() if js>0 else 0, stopped=js<len(fav))
        for k2 in (1,2,3): f[f'reach{k2}']=bool((fav[:js]>=k2).any())
        f['mfe_after_exit']=np.nan
        if pd.notna(r.t_out):
            jo=int(b.t.searchsorted(r.t_out.floor('15min'))); f['exit_vs_mfe']=f['R']/max(f['mfe'],1e-9) if f['mfe']>0 else np.nan
            E2=min(n,jo+192); f['after24h']=(((h[jo:E2].max()-r.px_out) if s==1 else (r.px_out-l[jo:E2].min()))/risk) if jo<n else np.nan
        out.append(f)
O=pd.DataFrame(out); O.to_pickle('outcome.pkl'); print(len(O))
