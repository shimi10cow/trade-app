import pandas as pd, numpy as np
exec(open('/home/user/trendlab/combo_app.py').read().split("def sim(")[0].replace("glob.glob('port/p_*.pkl')","glob.glob('/home/user/trendlab/port/p_*.pkl')").replace("f'parity_nt_{s}.pkl'","f'/home/user/trendlab/parity_nt_{s}.pkl'").replace("f'stoch/m15_{s}.pkl'","f'/home/user/trendlab/stoch/m15_{s}.pkl'"))
HALF={'S@XAUUSD':0.5,'Q@XAUUSD':0.5}
d=pd.read_pickle('/home/user/trendlab/rr/r_trades.pkl'); base=X[X.key!='R@EURUSD']; Rold=X[X.key=='R@EURUSD']
def mk(g):
    y=pd.DataFrame(dict(key='R@EURUSD',sym='EURUSD',t=g.t,exit_t=g.xt_h1a1,R=g.x_h1a1,side=g.side,et=pd.to_datetime(g.xt_h1a1)))
    y['mult']=Rold.set_index('t').mult.reindex(y.t).fillna(1.0).values; return y
V={'A 今のまま':Rold,'B R決済をH1追従（傾きゲートあり）':mk(d[d.sl4<0.35]),'C R決済をH1追従・傾きゲートなし':mk(d),'D Rをオフ':Rold.iloc[0:0]}
def path(R,m,w,risk,half):
    eq=pk=1.0; mdd=0.0
    for r,k,ww in zip(R,m,w):
        eq*=1+risk*k*ww*(0.5 if (half and eq<0.9*pk) else 1.0)*r; pk=max(pk,eq); mdd=min(mdd,eq/pk-1)
    return eq,mdd
for lab,r in V.items():
    Y=pd.concat([base,r]).sort_values('et'); R=Y.R.to_numpy(); w=Y.key.map(HALF).fillna(1.0).to_numpy(); M=Y.mult.to_numpy()
    yrs=(Y.et.max()-Y.et.min()).days/365.25; e=np.cumsum(R*w); ddR=(e-np.maximum.accumulate(np.r_[0,e])[1:]).min()
    ls=mx=0
    for x in R: ls=ls+1 if x<0 else 0; mx=max(mx,ls)
    out=[f'{lab}: 回数 {len(Y)}（年{len(Y)/yrs:.0f}） 勝率 {(R>0).mean():.1%} PF {R[R>0].sum()/-R[R<0].sum():.2f} 合計 {(R*w).sum():+.0f}R 最大DD {ddR:.1f}R 連敗 {mx}']
    for half in (True,False):
        s=[]
        for risk in (0.0075,0.01,0.015,0.02):
            eq,mdd=path(R,M,w,risk,half); s.append(f'{risk*100:g}%: {eq**(1/yrs)-1:+.0%}/{mdd:.1%}')
        out.append(('  半分あり ' if half else '  半分なし ')+'  '.join(s))
    print('\n'.join(out))
