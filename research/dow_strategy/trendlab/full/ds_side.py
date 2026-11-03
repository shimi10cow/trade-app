import sys; sys.path.insert(0,'/home/user/trade-app'); sys.path.insert(0,'/home/user/trade-app/research')
import pandas as pd, numpy as np, pickle
Y=pd.read_pickle('full/tp.pkl'); g=Y[Y.key=='DS@JP225'].copy(); cost=3e-4
F=pickle.load(open('live_frames_JP225.pkl','rb')); m=pd.read_pickle('stoch/m15_JP225.pkl'); T=m.time.to_numpy(); h,l,c=(m[z].to_numpy() for z in ('high','low','close'))
H1=(np.array([np.datetime64(x[0]) for x in F.H1P]),np.array([x[1] for x in F.H1P]),np.array([x[2] for x in F.H1P]))
def sim(i0,s,en,sl,tp=None,act=None):
    risk=abs(en-sl); on=False; TT,KK,PV=H1
    for j in range(i0+1,min(i0+96*30,len(c))):
        if (l[j]<=sl) if s==1 else (h[j]>=sl): return (sl-en)*s/risk
        if tp is not None and ((h[j]>=tp) if s==1 else (l[j]<=tp)): return (tp-en)*s/risk
        if act is not None:
            fav=((h[j]-en) if s==1 else (en-l[j]))/risk
            if not on and fav>=act: on=True
            if on:
                q=np.searchsorted(TT,T[j],side='left')-1; want='lo' if s==1 else 'hi'
                while q>=0 and KK[q]!=want: q-=1
                if q>=0 and (PV[q]-sl)*s>0 and (PV[q]-c[j])*s<0: sl=PV[q]
    j=min(i0+96*30,len(c))-1; return (c[j]-en)*s/risk
V={'1.5R利確':dict(k=1.5),'2R利確（今）':dict(k=2.0),'2.5R利確':dict(k=2.5),'3R利確':dict(k=3.0),'4R利確':dict(k=4.0),'+1RからH1':dict(act=1.0),'+2RからH1':dict(act=2.0)}
for lab,v in V.items():
    R=[]
    for x in g.itertuples():
        i0=int(np.searchsorted(T,np.datetime64(x.t))); s=int(x.side); risk=abs(x.entry-x.sl0)
        tp=x.entry+s*v['k']*risk if 'k' in v else None
        R.append(sim(i0,s,x.entry,x.sl0,tp,v.get('act'))-cost/risk)
    g[lab]=R
for s,nm in ((1,'買い'),(-1,'売り')):
    x=g[g.side==s]; print(f'\n== {nm}（{len(x)}回、前半 {(x.half==1).sum()}・後半 {(x.half==2).sum()}）')
    for lab in V:
        r=x[lab].to_numpy(); print(f'  {lab:10s} 勝率 {(r>0).mean():.0%} 平均 {r.mean():+.2f} 前半 {x[x.half==1][lab].mean():+.2f} 後半 {x[x.half==2][lab].mean():+.2f} 合計 {r.sum():+.1f} PF {r[r>0].sum()/-r[r<0].sum():.2f}')
