import numpy as np, pandas as pd
exec(open('combo_app.py').read().split("def sim(")[0])
HALF={'S@XAUUSD':0.5,'Q@XAUUSD':0.5}
X=X.sort_values('et').reset_index(drop=True); X['w']=X.key.map(HALF).fillna(1.0)
def sim(d,risk=0.01,half=True):
    eq=pk=1.0; mdd=0.0
    for r,k,w in zip(d.R,d.mult,d.w):
        eq*=1+risk*k*w*(0.5 if (half and eq<0.9*pk) else 1.0)*r; pk=max(pk,eq); mdd=min(mdd,eq/pk-1)
    yrs=(d.et.max()-d.et.min()).days/365.25; return eq**(1/yrs)-1, mdd
def ddR(d):
    e=np.cumsum(d.R*d.w); return (e-np.maximum.accumulate(np.r_[0,e])[1:]).min()
# monthly R for correlation with the rest
Mo=X.groupby([X.et.dt.to_period('M'),'key']).apply(lambda g:(g.R*g.w).sum()).unstack(fill_value=0)
base=sim(X); half=(X.et>='2016-01-01')
print(f'全体: 年利 {base[0]:+.1%} DD {base[1]:.1%} 比 {base[0]/-base[1]:.2f}  DD(R) {ddR(X):.1f}')
rows=[]
for k in sorted(X.key.unique()):
    d=X[X.key!=k]; c,dd=sim(d); g=X[X.key==k]
    rest=Mo.drop(columns=k).sum(axis=1); corr=np.corrcoef(Mo[k],rest)[0,1]
    h1=g[g.et<'2016'].R.mean(); h2=g[g.et>='2016'].R.mean()
    rows.append(dict(EA=k,回数=len(g),PF=round(g.R[g.R>0].sum()/-g.R[g.R<0].sum(),2),平均R=round(g.R.mean(),2),前半=round(h1,2) if np.isfinite(h1) else None,後半=round(h2,2),
                     外した年利=f'{c:+.1%}',外したDD=f'{dd:.1%}',年利の差=round((c-base[0])*100,1),DDの差=round((dd-base[1])*100,1),比の差=round(c/-dd-base[0]/-base[1],2),相関=round(corr,2)))
r=pd.DataFrame(rows).sort_values('比の差',ascending=False)
pd.set_option('display.width',250); print(r.to_string(index=False))
print()
d=X[X.key!='R@EURUSD']
for lab,kw in [('1% 半分あり',{}),('0.75% 半分あり',dict(risk=0.0075)),('1% 半分なし',dict(half=False)),('1.5% 半分あり',dict(risk=0.015))]:
    a=sim(X,**kw); b=sim(d,**kw); print(f'{lab}: 全部 {a[0]:+.0%}/{a[1]:.1%}  R抜き {b[0]:+.0%}/{b[1]:.1%}')
print('DD(R) 全部',round(ddR(X),1),'R抜き',round(ddR(d),1))
g=X[X.key=='R@EURUSD']; print(g.groupby(g.et.dt.year).R.sum().round(1).to_dict())
# where is the portfolio max DD (1%, half)?
eq=pk=1.0; worst=(0,None,None); peak_t=None
for t,r,k,w in zip(X.et,X.R,X.mult,X.w):
    eq*=1+0.01*k*w*(0.5 if eq<0.9*pk else 1)*r
    if eq>pk: pk=eq; peak_t=t
    if eq/pk-1<worst[0]: worst=(eq/pk-1,peak_t,t)
print('全体の最大DDの期間',worst)
s=X[(X.et>worst[1])&(X.et<=worst[2])]; print(s.groupby('key').apply(lambda x:(x.R*x.w).sum()).sort_values().round(1).head(8).to_dict())
