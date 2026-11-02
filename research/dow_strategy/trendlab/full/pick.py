import pandas as pd, numpy as np
exec(open('full/eval.py').read().split("# ---------- 1 filters")[0])
SEL={'C@EURUSD':'伸び<=6ATR','A@EURUSD':'伸び<=6ATR','T@US30':'水平帯の反発なし'}
EXIT=['J2@USDJPY']
Y=base.copy()
for k,fn in SEL.items(): Y=Y[~((Y.key==k)&~FILT[fn](Y).fillna(False))]
Z=Y.copy(); m=Z.key.isin(EXIT)&Z.R_h1.notna(); Z.loc[m,'R']=Z.loc[m,'R_h1']; Z.loc[m,'exit_t']=Z.loc[m,'exit_h1']
for lab,X in (('今',base),('条件5つ',Y),('条件5つ＋J2決済',Z)):
    s=[port(X,r,h) for r,h in ((0.0075,True),(0.01,True),(0.015,True),(0.02,True),(0.01,False))]
    per=[]
    for a,b in (('2005','2012'),('2012','2019'),('2019','2027')):
        x=X[(X.t>=a)&(X.t<b)]; per.append(port(x))
    R=X.R.to_numpy()
    print(f"{lab:14s} 回数 {len(X)} 勝率 {(R>0).mean():.1%} PF {R[R>0].sum()/-R[R<0].sum():.2f} | "+'  '.join(f'{a:+.0%}/{b:.1%}' for a,b in s)+' | 3期間 '+' '.join(f'{a:+.0%}/{b:.0%}' for a,b in per))
print()
for k,fn in SEL.items():
    g=base[base.key==k]; out=g[~FILT[fn](g).fillna(False)]
    print(f"{k:10s} {fn:10s} 外れる {len(out)}/{len(g)}  外れる分の平均R 前半 {out[out.half==1].R.mean():+.2f}（{(out.half==1).sum()}回） 後半 {out[out.half==2].R.mean():+.2f}（{(out.half==2).sum()}回） 合計 {out.R.sum():+.1f}R")
