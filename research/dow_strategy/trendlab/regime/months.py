import pandas as pd, numpy as np
T=pd.read_pickle('regime/trades.pkl'); DAY=pd.read_pickle('regime/days.pkl')
# monthly portfolio R by exit month vs share of symbol-days in each regime
mo=T.groupby(T.exit_t.dt.to_period('M')).Rw.sum()
parts=[]
for s,d in DAY.items():
    x=pd.DataFrame(dict(opp=(d.wd=='opp'),same=(d.wd=='same'),rng=d.rng.astype(bool),conv=d.conv.astype(bool),big=d.big.astype(bool)),index=d.index); parts.append(x)
share=pd.concat(parts).groupby(lambda t: pd.Period(t,'M')).mean()
J=share.join(mo.rename('R'),how='inner'); J=J[(J.index>=pd.Period('2006-01','M'))&(J.index<=pd.Period('2026-09','M'))]
J['q']=pd.qcut(J.R.rank(method='first'),5,labels=['最悪2割','2','3','4','最良2割'])
print('月の成績の5分位ごとの局面の割合（全銘柄の日数の割合）'); print(J.groupby('q')[['opp','same','rng','conv','big','R']].mean().round(3).to_string())
print('\n相関（月の R と局面の割合）'); print(J[['opp','same','rng','conv','big']].corrwith(J.R).round(2).to_string())
# per EA: trades against the weekly trend
print('\nEA ごと：週足と逆向きの入り（平均R 前半/後半、回数）')
rows=[]
for k,g in T.groupby('key'):
    a=g[g.with_wk=='W逆']; b=g[g.with_wk!='W逆']
    rows.append(dict(EA=k,逆_回数=len(a),逆_前半=a[a.t<'2016'].R.mean(),逆_後半=a[a.t>='2016'].R.mean(),他_前半=b[b.t<'2016'].R.mean(),他_後半=b[b.t>='2016'].R.mean(),逆_合計=a.R.sum()))
print(pd.DataFrame(rows).round(2).sort_values('逆_合計').to_string(index=False))
