import sys; sys.path.insert(0,'/home/user/trade-app'); sys.path.insert(0,'/home/user/trade-app/research')
import pandas as pd, numpy as np, pickle
Y=pd.read_pickle('full/tp.pkl'); COSTS={'US500':2e-4,'JP225':3e-4}
for k in ('DS@JP225','DS@US500'):
    s_=k.split('@')[1]; F=pickle.load(open(f'live_frames_{s_}.pkl','rb'))
    m=pd.read_pickle(f'stoch/m15_{s_}.pkl'); T=m.time.to_numpy(); h,l,c=(m[z].to_numpy() for z in ('high','low','close'))
    def arr(P): return np.array([np.datetime64(x[0]) for x in P]), np.array([x[1] for x in P]), np.array([x[2] for x in P])
    M15=arr(F.P15); H1=arr(F.H1P)
    def sim(i0,s,en,sl,act,src):
        risk=abs(en-sl); on=False; TT,KK,PV=M15 if src=='m15' else H1
        for j in range(i0+1,min(i0+96*30,len(c))):
            if (l[j]<=sl) if s==1 else (h[j]>=sl): return (sl-en)*s/risk
            fav=((h[j]-en) if s==1 else (en-l[j]))/risk
            if not on and fav>=act: on=True
            if on:
                q=np.searchsorted(TT,T[j],side='left')-1; want='lo' if s==1 else 'hi'
                while q>=0 and KK[q]!=want: q-=1
                if q>=0 and (PV[q]-sl)*s>0 and (PV[q]-c[j])*s<0: sl=PV[q]
        j=min(i0+96*30,len(c))-1; return (c[j]-en)*s/risk
    g=Y[Y.key==k]; print(f'\n{k} ({len(g)}回)')
    for lab,act,src in [('+1RからH1で追う',1.0,'h1'),('+1.5RからH1で追う',1.5,'h1'),('+2RからH1で追う',2.0,'h1'),('+2.5RからH1で追う',2.5,'h1'),('+3RからH1で追う',3.0,'h1')]:
        R=np.array([sim(int(np.searchsorted(T,np.datetime64(x.t))),int(x.side),x.entry,x.sl0,act,src)-COSTS[s_]/abs(x.entry-x.sl0) for x in g.itertuples()])
        hv=g.half.to_numpy(); e=np.cumsum(R); dd=(e-np.maximum.accumulate(np.r_[0,e])[1:]).min(); sr=np.sort(R)[::-1]
        print(f'  {lab:16s} 勝率 {(R>0).mean():.0%} 平均 {R.mean():+.3f} 前半 {R[hv==1].mean():+.2f} 後半 {R[hv==2].mean():+.2f} 合計 {R.sum():+.1f} PF {R[R>0].sum()/-R[R<0].sum():.2f} DD {dd:.1f} 上位5 {sr[:5].sum()/R.sum():.0%}')
