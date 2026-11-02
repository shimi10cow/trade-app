import pandas as pd, numpy as np, glob
SPLIT={'EURUSD':'2016','USDJPY':'2016','XAUUSD':'2016','XAGUSD':'2016','US30':'2020-07','US500':'2021-10','JP225':'2021-10','BTCUSD':'2022'}
d=pd.concat([pd.read_pickle(f) for f in glob.glob('mr/m_*.pkl')],ignore_index=True)
d['half']=[1 if t<pd.Timestamp(SPLIT[s]) else 2 for s,t in zip(d.sym,d.t)]
yrs=d.groupby('sym').t.agg(lambda x:(x.max()-x.min()).days/365.25)
# check vs live M
x=d[(d.tf=='D1')&(d.lo==10)&(d.stop=='a25')&(d.ex=='ma5')&d.sym.isin(['US30','US500'])]; print('今のM相当:',x.groupby('sym').R.agg(['count','sum','mean']).round(2).to_dict())
def st(g):
    r=g.R.to_numpy(); s=g.name[-1]
    return pd.Series(dict(n_yr=len(r)/yrs[s],win=(r>0).mean(),h1=g[g.half==1].R.mean(),h2=g[g.half==2].R.mean(),PF=r[r>0].sum()/max(-r[r<0].sum(),1e-9),Ryr=r.sum()/yrs[s],
        top5=np.sort(r)[::-1][:5].sum()/r.sum() if r.sum()>0 else np.nan,lossavg=r[r<0].mean(),stopw=g.riskp.median()))
S=d.groupby(['tf','lo','stop','ex','sym']).apply(st)
S['ok']=(S.h1>0.05)&(S.h2>0.05)&(S.PF>1.2)
agg=S.groupby(['tf','lo','stop','ex']).agg(syms_ok=('ok','sum'),n_yr=('n_yr','sum'),Ryr=('Ryr','sum'),win=('win','mean'),PF=('PF','median'))
pd.set_option('display.width',250); pd.set_option('display.max_rows',200)
print(agg.sort_values(['syms_ok','Ryr'],ascending=False).head(25).round(2).to_string())
S.to_pickle('mr/S.pkl')
