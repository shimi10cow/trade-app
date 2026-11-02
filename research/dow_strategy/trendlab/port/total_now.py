import numpy as np, pandas as pd, sys
exec(open('combo_app.py').read().split("def sim(")[0])          # builds X (22 EAs, gates, P, calendar mult)
HALF={'S@XAUUSD':0.5,'Q@XAUUSD':0.5}
X=X.sort_values('et').reset_index(drop=True); X['w']=X.key.map(HALF).fillna(1.0)
R=X.R.to_numpy(); yrs=(X.et.max()-X.et.min()).days/365.25
eqR=np.cumsum(R*X.w); ddR=(eqR-np.maximum.accumulate(np.r_[0,eqR])[1:]).min()
ls=mx=0
for r in R:
    ls=ls+1 if r<0 else 0; mx=max(mx,ls)
print(f'期間 {X.t.min():%Y-%m}〜{X.et.max():%Y-%m}（{yrs:.1f}年） 回数 {len(X)}（年 {len(X)/yrs:.0f}、月 {len(X)/yrs/12:.0f}） 勝率 {(R>0).mean():.1%} PF {R[R>0].sum()/-R[R<0].sum():.2f} 平均 {R.mean():+.3f}R 合計(重み込み) {(R*X.w).sum():+.0f}R 最大DD {ddR:.1f}R 最大連敗 {mx}')
def path(R,m,w,risk,half):
    eq=pk=1.0; mdd=0.0
    for r,k,ww in zip(R,m,w):
        eq*=1+risk*k*ww*(0.5 if (half and eq<0.9*pk) else 1.0)*r; pk=max(pk,eq); mdd=min(mdd,eq/pk-1)
    return eq,mdd
rng=np.random.default_rng(1); n_yr=int(round(len(X)/yrs)); M=X.mult.to_numpy(); W=X.w.to_numpy()
for half in (True,False):
    print('\n== DD10%で半分', 'あり' if half else 'なし')
    for risk in (0.0075,0.01,0.015,0.02):
        eq,mdd=path(R,M,W,risk,half); cagr=eq**(1/yrs)-1
        # yearly returns in history
        y=[]; e=1.0; pk=1.0
        for yr,g in X.groupby(X.et.dt.year):
            e0=e
            for r,k,ww in zip(g.R,g.mult,g.w):
                e*=1+risk*k*ww*(0.5 if (half and e<0.9*pk) else 1.0)*r; pk=max(pk,e)
            y.append(e/e0-1)
        y=np.array(y[1:-1])
        res={}
        for N in (1,3,5):
            ends=[];dds=[]
            for _ in range(800):
                idx=rng.integers(0,len(R),n_yr*N); e2,d2=path(R[idx],M[idx],W[idx],risk,half); ends.append(e2); dds.append(d2)
            ends=np.array(ends); res[N]=(np.median(ends),np.percentile(ends,10),np.percentile(ends,90),np.mean(np.array(dds)<-0.3) if N==1 else None, np.percentile(dds,10))
        print(f'リスク {risk*100:.2f}%: 年利 {cagr:+.0%}  最大DD {mdd:.1%}  最悪の年 {y.min():+.0%} マイナスの年 {(y<0).sum()}/{len(y)}  | 100万円→ 1年後 {res[1][0]*100:.0f}万（悪い1割 {res[1][1]*100:.0f}万） 3年後 {res[3][0]*100:.0f}万（{res[3][1]*100:.0f}万） 5年後 {res[5][0]*100:.0f}万（{res[5][1]*100:.0f}万）  1年でDD30%超の確率 {res[1][3]:.0%}  5年の間のDD(悪い1割) {res[5][4]:.0%}')
