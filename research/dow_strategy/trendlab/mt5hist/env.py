"""EA environment reading at the real entry time of every MT5 trade (broker M15 bars, causal)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from mt5_ea.live.eas import l as EL, c as EC
from env_recognition import dow_trend
from env_recognition.pivots import atr
LOGS={'GOLD','SILVER','US500','JP225','EU50','UK100','US30','BTCJPY','BTCUSD','BTCGBP','OIL','BRENT','XAUEUR','NATGAS','NGAS','GER40','US100'}
O=pd.read_pickle('outcome.pkl'); T=pd.read_pickle('trades_mt5.pkl').set_index('tid')
sym=sys.argv[1]; g=O[O.symbol==sym]
b=pd.read_csv(f'bars_{sym}.csv.gz'); b['t']=pd.to_datetime(b.time); m=b.rename(columns=dict(open='o',high='h',low='l',close='c'))[['t','o','h','l','c']]
for z in 'ohlc':
    if sym in LOGS: m[z]=np.log(m[z])
    elif sym.endswith('JPY'): m[z]=m[z]/100
class Shim: pass
rows=[]
for _,r in g.iterrows():
    s=r.s; want='up' if s==1 else 'down'; t=T.loc[r.tid,'t_in'].floor('15min')
    w=m[(m.t>=t-pd.Timedelta(days=440))&(m.t<t)].reset_index(drop=True)
    if len(w)<3000: continue
    try: F=Frames(w,t-pd.Timedelta(days=2))
    except Exception as ex: print('skip',ex); continue
    if len(F.h4)<120: continue
    f=dict(tid=r.tid)
    d1=F.h4.set_index('t').resample('1D').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index(); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
    RD=dow_trend.run(d1,'D1') if len(d1)>80 else None
    f['D1']=float(RD['bars'][-1][0]==want) if RD else np.nan; f['H4']=float(F.R4['bars'][-1][0]==want); f['H1']=float(F.R1['bars'][-1][0]==want)
    A4=atr(F.h4); a=A4[-1]; k=len(F.h4)-1; bars4=F.R4['bars']; lv={}
    if bars4[k][0]==want and bars4[k][1] is not None: lv['砦']=bars4[k][1]
    rev=[x for x in F.R4['events'] if x.get('machine')=='major' and x['action']=='REVERSAL']
    if rev and rev[-1]['to']==want: lv['出入口']=rev[-1]['broken_price']
    for q,x in enumerate([x for x in F.R4['pivot_events'] if x['action']=='confirm' and x['kind']==('lo' if s==1 else 'hi')][-3:]): lv[f'H4山谷{q}']=x['price']
    if RD:
        for q,x in enumerate([x for x in RD['pivot_events'] if x['action']=='confirm' and x['kind']==('lo' if s==1 else 'hi')][-3:]): lv[f'D1山谷{q}']=x['price']
    h1=F.h1; lo24=h1.l.iloc[-24:].min(); hi24=h1.h.iloc[-24:].max(); c=h1.c.iat[-1]
    hits=[nm for nm,L_ in lv.items() if ((L_-0.3*a<=lo24<=L_+0.5*a and c>L_) if s==1 else (L_+0.3*a>=hi24>=L_-0.5*a and c<L_))]
    f['帯']=float(bool(hits)); f['砦']=float('砦' in hits); f['出入口']=float('出入口' in hits); f['H4山谷']=float(any(x.startswith('H4山谷') for x in hits)); f['D1山谷']=float(any(x.startswith('D1山谷') for x in hits))
    cc=h1.c; m20=cc.rolling(20).mean().to_numpy(); m75=cc.rolling(75).mean().to_numpy(); A1=atr(h1); up=m20>m75
    f['MA向き']=float(up[-1]==(s==1)); f['MA75傾き']=(m75[-1]-m75[-11])*s/A1[-1]; f['MA20距離']=(c-m20[-1])*s/A1[-1]
    cr=np.flatnonzero(up[1:]!=up[:-1]); i0=cr[-1]+1 if len(cr) else 0; f['クロスから']=len(cc)-1-i0
    hi_,lo_=h1.h.to_numpy(),h1.l.to_numpy(); ext=None; newx=True; kk=0; inpb=False
    for i in range(i0,len(cc)):
        x_=hi_[i] if s==1 else lo_[i]
        if ext is None or (x_-ext)*s>0: ext=x_; newx=True; inpb=False; continue
        near=(lo_[i]<=m20[i]+0.25*A1[i]) if s==1 else (hi_[i]>=m20[i]-0.25*A1[i])
        if newx and near and not inpb: kk+=1; inpb=True; newx=False
    f['押し回数']=kk if f['MA向き'] else -1
    tl=[]
    for tf,df,R,C,A_ in (('H4',F.h4,F.R4,F.C4,A4),('H1',F.h1,F.R1,F.C1,A1)):
        for x in EL.line_touches(df,R,C,A_,tf):
            if x['kind']=='touch' and x['d']==want and pd.Timestamp(x['t'])>=t-pd.Timedelta('48h'): tl.append(tf)
    f['推進H4']=float('H4' in tl); f['推進H1']=float('H1' in tl)
    L15,_=EC.lines(F); f['M15逆トレ抜け']=float(any(x[7] and ((x[6]=='hi')==(s==1)) and F.T15[x[5]]>=t-pd.Timedelta('8h') for x in L15))
    S=Shim(); S.h,S.l,S.c=(h1[z].to_numpy(float) for z in 'hlc'); S.m15=h1; S.T15=pd.to_datetime(h1.t); S.R15=F.R1
    old=(EC.LOOK,EC.IMPW,EC.IMP); EC.LOOK,EC.IMPW,EC.IMP=20,48,5.0; L1,_=EC.lines(S); EC.LOOK,EC.IMPW,EC.IMP=old
    f['H1逆トレ抜け']=float(any(x[7] and ((x[6]=='hi')==(s==1)) and S.T15[x[5]]>=t-pd.Timedelta('24h') for x in L1))
    pv=[x for x in F.R15['prov_events'] if x['action'] in('REVERSAL','PROV_START') and x['to']==want]
    f['M15転換4h']=float(bool(pv and F.T15[pv[-1]['idx']]>=t-pd.Timedelta('4h')))
    f['M15ダウ一致']=float(F.R15['bars'][-1][0]==want)
    c4=F.h4.c.to_numpy(); f['H4効率30']=abs(c4[-1]-c4[-31])/np.abs(np.diff(c4[-31:])).sum()
    sma=pd.Series(c4).rolling(min(1200,len(c4)-1)).mean().to_numpy(); f['日足側']=float((c4[-1]-sma[-1])*s>0) if len(c4)>300 else np.nan
    f['時刻JST']=T.loc[r.tid,'tj_in'].hour
    rows.append(f)
pd.DataFrame(rows).to_pickle(f'env_{sym}.pkl'); print('done',sym,len(rows),flush=True)
