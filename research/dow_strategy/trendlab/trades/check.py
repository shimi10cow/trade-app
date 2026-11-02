import sys, numpy as np, pandas as pd
X=pd.read_pickle('trades.pkl')
M={}
def m15(sym):
    if sym not in M: M[sym]=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl')
    return M[sym]
rows=[]
for _,r in X.iterrows():
    m=m15(r.sym); T=m.time; i=int(T.searchsorted(r.tb)); h=m.high.to_numpy(); l=m.low.to_numpy(); c=m.close.to_numpy(); n=len(c)
    s=r.s; en=r.en; risk=abs(en-r.sl); E=min(n,i+960)
    fav=((h[i:E]-en) if s==1 else (en-l[i:E]))/risk; adv=((en-l[i:E]) if s==1 else (h[i:E]-en))/risk
    stop=np.flatnonzero(adv>=1); js=stop[0] if len(stop) else len(fav)
    f=dict(id=r.id,sym=r.sym,tj=r.tj,R=r.R,win=r.win)
    f['mfe_before_stop']=fav[:js].max() if js>0 else 0
    for k in (1,2,3): f[f'reach{k}']=bool((fav[:js]>=k).any())
    f['mfe5d_any']=fav[:min(len(fav),480)].max()
    # random-walk benchmark for reaching +kR before -1R: 1/(1+k)
    # break-even stop: after +x R, stop to entry. Stopped at BE? then later reached +2R / +3R?
    for x in (0.5,1.0):
        jx=np.flatnonzero(fav[:js]>=x)
        if len(jx)==0: f[f'be{x}']='届かず'; continue
        j0=jx[0]; back=np.flatnonzero(adv[j0:]>=0)   # price back to entry
        if len(back)==0: f[f'be{x}']='建値に戻らず'; continue
        jb=j0+back[0]
        if (fav[j0:jb+1]>=2).any(): f[f'be{x}']='建値前に+2R'; continue
        later=fav[jb:].max(); f[f'be{x}']='建値で切られ→+2R以上' if later>=2 else '建値で切られ→伸びず'
        f[f'be{x}_save']=bool((adv[jb:]>=1).any())   # without BE the original stop would have been hit later
    rows.append(f)
D=pd.DataFrame(rows); D.to_pickle('check.pkl')
for nm,d in [('全63件',D),('2026年3月以降',D[D.tj>='2026-03-01']),('2026年5月以降',D[D.tj>='2026-05-01'])]:
    print(f"== {nm} n{len(d)}")
    for k in (1,2,3): print(f"   損切りの前に +{k}R に届いた {d[f'reach{k}'].mean()*100:3.0f}%   （ランダムなら {100/(1+k):.0f}%）")
    print(f"   損切りまでの最大の伸び 中央 {d.mfe_before_stop.median():.2f}R")
    for x in (0.5,1.0):
        vc=d[f'be{x}'].value_counts(); print(f"   +{x}Rで建値に上げた場合:", vc.to_dict())
        sub=d[d[f'be{x}'].astype(str).str.startswith('建値で切られ')]
        if len(sub): print(f"      建値で切られたうち、上げなければ元の損切りにも当たった {sub[f'be{x}_save'].mean()*100:.0f}%")
pd.set_option('display.width',200)
print(D[D.tj>='2026-05-01'][['tj','sym','R','mfe_before_stop','reach1','reach2','reach3','be0.5','be1.0']].round(2).to_string())
