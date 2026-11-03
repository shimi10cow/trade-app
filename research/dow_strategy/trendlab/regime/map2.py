import pandas as pd, numpy as np
X=pd.read_pickle('full/current.pkl'); S=pd.read_pickle('regime/dow_states.pkl')
def cls(d):
    wd=np.where((d.WM!=0)&(d.DM==d.WM),'同じ向き',np.where((d.WM!=0)&(d.DM==-d.WM),'週足の調整中',np.where(d.WM==0,'週足トレンドなし','日足トレンドなし')))
    return pd.DataFrame(dict(wd=wd,win=np.where(d.W_in.astype(bool),'週足レンジの中','週足レンジの外'),din=np.where(d.D_in.astype(bool),'日足レンジの中','日足レンジの外'),WM=d.WM),index=d.index)
C={s:cls(d) for s,d in S.items()}
rows=[]
for s,g in X.groupby('sym'):
    c=C[s]; k=c.index.searchsorted(g.t,side='right')-1; ok=k>=0; g=g[ok].copy(); r=c.iloc[k[ok]]
    for col in ('wd','win','din'): g[col]=r[col].to_numpy()
    g['vsW']=np.where(r.WM.to_numpy()==0,'週足なし',np.where(r.WM.to_numpy()*g.side>0,'週足と同じ向き','週足と逆向き')); rows.append(g)
T=pd.concat(rows,ignore_index=True); T['Rw']=T.R*T.w; T.to_pickle('regime/trades2.pkl')
syms=sorted(X.sym.unique())
def tab(col,lab):
    dd=pd.concat([C[s][col].value_counts() for s in syms],axis=1).sum(axis=1)
    g=T.groupby(col).agg(回数=('R','size'),平均R=('R','mean'),合計R=('Rw','sum'))
    g['期間の割合']=dd/dd.sum(); g['100日あたりR']=g.合計R/dd*100; g['前半']=T[T.t<'2016'].groupby(col).R.mean(); g['後半']=T[T.t>='2016'].groupby(col).R.mean()
    print(f'\n== {lab}'); print(g.round(3).to_string())
tab('wd','週足・日足のダウ'); tab('win','週足の高値・安値の中（週足レンジ）'); tab('din','日足の高値・安値の中（日足レンジ）')
T['wd_win']=T.wd+'／'+T.win
for s in syms: C[s]['wd_win']=C[s].wd+'／'+C[s].win
tab('wd_win','組み合わせ')
# bad months
mo=T.groupby(T.exit_t.dt.to_period('M')).Rw.sum(); parts=[]
for s in syms:
    c=C[s]; parts.append(pd.DataFrame(dict(調整=(c.wd=='週足の調整中'),同じ=(c.wd=='同じ向き'),週足レンジ=(c.win=='週足レンジの中'),日足レンジ=(c.din=='日足レンジの中')),index=c.index))
sh=pd.concat(parts).groupby(lambda t: pd.Period(t,'M')).mean(); J=sh.join(mo.rename('R'),how='inner'); J=J[(J.index>=pd.Period('2006-01','M'))]
J['q']=pd.qcut(J.R.rank(method='first'),5,labels=['最悪2割','2','3','4','最良2割'])
print('\n== 月の成績ごとの局面の割合'); print(J.groupby('q').mean(numeric_only=True).round(3).to_string())
g=T.groupby('vsW').agg(回数=('R','size'),平均R=('R','mean'),合計R=('Rw','sum')); g['前半']=T[T.t<'2016'].groupby('vsW').R.mean(); g['後半']=T[T.t>='2016'].groupby('vsW').R.mean()
print('\n== トレードの向き × 週足のダウ'); print(g.round(3).to_string())
