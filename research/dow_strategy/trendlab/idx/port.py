import sys, pandas as pd, numpy as np
sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.sizing import calendar_mult
X=pd.read_pickle('full/current.pkl')[['key','sym','t','exit_t','R','side','w','mult']]
I=pd.read_pickle('idx/all.pkl'); M=pd.read_pickle('idx/m_all.pkl')
days={}
def tdm(s,t):
    if s not in days:
        d=pd.read_pickle(f'idx/d1_{s}.pkl').time; dd=pd.DatetimeIndex(d.dt.normalize().unique()); days[s]=pd.Series(1,index=dd).groupby([dd.year,dd.month]).cumsum()
    ser=days[s]; d=pd.Timestamp(t).normalize(); i=ser.index.searchsorted(d,side='right')-1
    return int(ser.iloc[i]) if i>=0 and ser.index[i].month==d.month and ser.index[i].year==d.year else 1
def mk(df,key):
    y=pd.DataFrame(dict(key=key,sym=df.sym.values,t=pd.to_datetime(df.t.values),exit_t=pd.to_datetime(df.exit_t.values),R=df.R.values,side=df.side.astype(int).values,w=1.0))
    y['mult']=[calendar_mult(s,sd,t,tdm(s,t)) for s,sd,t in zip(y.sym,y.side,y.t)]; return y
C={'P@GER40':mk(I[I.key=='P@GER40'],'P@GER40'),'P@US100':mk(I[I.key=='P@US100'],'P@US100'),'P@US500':mk(I[I.key=='P@US500'],'P@US500'),
   'Q@BRENT':mk(I[I.key=='Q_us30@BRENT'],'Q@BRENT')}
for s in ('US100','GER40','EU50'):
    C[f'M@{s}']=mk(M[(M.sym==s)&(M.cfg=='今のM（RSI<10・2.5ATR・SMA5で決済）')],f'M@{s}')
def port(X,risk=0.01,half=True):
    X=X.sort_values('exit_t'); eq=pk=1.0; mdd=0.0
    for r,k,w in zip(X.R,X.mult,X.w):
        eq*=1+risk*k*w*(0.5 if (half and eq<0.9*pk) else 1.0)*r; pk=max(pk,eq); mdd=min(mdd,eq/pk-1)
    yrs=(X.exit_t.max()-X.t.min()).days/365.25; return eq**(1/yrs)-1, mdd
mo=X.assign(Rw=X.R*X.w).groupby(X.exit_t.dt.to_period('M')).Rw.sum(); bad=set(mo[mo<=mo.quantile(0.2)].index)
base=port(X); base2=port(X,0.02); print(f'今の21本: 1% {base[0]:+.1%}/{base[1]:.1%}  2% {base2[0]:+.0%}/{base2[1]:.1%}')
for k,y in C.items():
    a=port(pd.concat([X,y])); b=port(pd.concat([X,y]),0.02)
    m=y.groupby(y.exit_t.dt.to_period('M')).R.sum(); j=pd.concat([m,mo],axis=1).fillna(0); j=j[j.index>=y.t.min().to_period('M')]
    inbad=y[y.exit_t.dt.to_period('M').isin(bad)].R.sum(); yrs=(y.exit_t.max()-y.t.min()).days/365.25
    print(f'{k:9s} 年{len(y)/yrs:4.1f}回 年{y.R.sum()/yrs:+.1f}R 相関 {j.iloc[:,0].corr(j.iloc[:,1]):+.2f} 悪い月の合計 {inbad:+.1f}R | 足すと 1% {a[0]:+.1%}/{a[1]:.1%}  2% {b[0]:+.0%}/{b[1]:.1%}')
ALL=pd.concat([X]+list(C.values())); a=port(ALL); b=port(ALL,0.02); c=port(ALL,half=False)
print(f'全部足す: 1% {a[0]:+.1%}/{a[1]:.1%}  2% {b[0]:+.0%}/{b[1]:.1%}  1%半分なし {c[0]:+.0%}/{c[1]:.1%}')
pd.to_pickle(C,'idx/cands.pkl')
