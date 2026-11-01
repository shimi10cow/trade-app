"""User's recorded trades vs the live EA's own environment reading at the entry time (causal: bars up to the entry only)."""
import sys, bisect, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from mt5_ea.live.eas import l as EL, c as EC
from env_recognition import dow_trend
from env_recognition.pivots import atr
EL.ULOOK['D1']=20
LOGS={'XAUUSD','US500','JP225'}
e=pd.read_excel('/home/user/sheet/book.xlsx','Entries'); e=e[e.TrashedAt.isna()]
e['pair']=e['PairName（元）'].replace({'CHEJPY':'CHFJPY'})
HAVE=['EURUSD','GBPUSD','AUDUSD','USDCAD','USDCHF','USDJPY','EURJPY','AUDJPY','CADJPY','CHFJPY','XAUUSD','US500','JP225','OIL','NGAS']
e=e[e.pair.isin(HAVE)&e.Direction.isin(['Buy','Sell'])&e.EntryTime.notna()].copy()
e['tj']=[pd.Timestamp(d.date())+pd.Timedelta(str(t)) for d,t in zip(e.EntryDate,e.EntryTime)]
e['tb']=[t-pd.Timedelta(hours=6 if 4<=t.month<=10 else 7) for t in e.tj]
M={}
def m15(sym):
    if sym not in M:
        m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
        if sym in LOGS:
            for z in 'ohlc': m[z]=np.log(m[z])
        if sym.endswith('JPY'):
            for z in 'ohlc': m[z]=m[z]/100
        M[sym]=m
    return M[sym]
class Shim: pass
rows=[]
for _,r in e.iterrows():
    sym=r.pair; s=1 if r.Direction=='Buy' else -1; t=r.tb; want='up' if s==1 else 'down'
    m=m15(sym); w=m[(m.t>=t-pd.Timedelta(days=440))&(m.t<t)].reset_index(drop=True)      # bars that closed before entry
    if len(w)<20000: continue
    F=Frames(w,t-pd.Timedelta(days=2))
    f=dict(id=r.EntryID,sym=sym,s=s,tj=r.tj,tb=t,win=r['勝敗'],Rr=r['実リスクリワード'])
    # dow
    d1=F.h4.set_index('t').resample('1D').agg(dict(o='first',h='max',l='min',c='last')).dropna().reset_index(); d1=d1[d1.t.dt.dayofweek<5].reset_index(drop=True)
    RD=dow_trend.run(d1,'D1')
    f['eD1']=RD['bars'][-1][0]; f['eH4']=F.R4['bars'][-1][0]; f['eH1']=F.R1['bars'][-1][0]
    # H4 levels hit by the last 24 H1 bars
    A4=atr(F.h4); a=A4[-1]; k=len(F.h4)-1; bars4=F.R4['bars']
    lv={}
    if bars4[k][0]==want and bars4[k][1] is not None: lv['砦']=bars4[k][1]
    rev=[x for x in F.R4['events'] if x.get('machine')=='major' and x['action']=='REVERSAL']
    if rev and rev[-1]['to']==want: lv['出入口']=rev[-1]['broken_price']
    sw=[x for x in F.R4['pivot_events'] if x['action']=='confirm' and x['kind']==('lo' if s==1 else 'hi')][-3:]
    for q,x in enumerate(sw): lv[f'山谷{q}']=x['price']
    # D1 swings too (user: 水平線 D1・H4)
    swd=[x for x in RD['pivot_events'] if x['action']=='confirm' and x['kind']==('lo' if s==1 else 'hi')][-3:]
    for q,x in enumerate(swd): lv[f'日足山谷{q}']=x['price']
    h1=F.h1; lo24=h1.l.iloc[-24:].min(); hi24=h1.h.iloc[-24:].max(); c=h1.c.iat[-1]
    hits=[n for n,L_ in lv.items() if ((L_-0.3*a<=lo24<=L_+0.5*a and c>L_) if s==1 else (L_+0.3*a>=hi24>=L_-0.5*a and c<L_))]
    f['e水平線']=','.join(hits)
    # H1 MA
    cc=h1.c; m20=cc.rolling(20).mean().to_numpy(); m75=cc.rolling(75).mean().to_numpy(); A1=atr(h1)
    up=m20>m75; f['eMA向き']=bool(up[-1]==(s==1))
    cr=np.flatnonzero(up[1:]!=up[:-1]); i0=cr[-1]+1 if len(cr) else 0; f['eクロスから']=len(cc)-1-i0
    # pullback count since cross: times low came within 0.25 ATR of MA20 after a new extreme
    hi_,lo_=h1.h.to_numpy(),h1.l.to_numpy(); ext=None; newx=True; k_=0; inpb=False
    for i in range(i0,len(cc)):
        x_=hi_[i] if s==1 else lo_[i]
        if ext is None or (x_-ext)*s>0: ext=x_; newx=True; inpb=False; continue
        near=(lo_[i]<=m20[i]+0.25*A1[i]) if s==1 else (hi_[i]>=m20[i]-0.25*A1[i])
        if newx and near and not inpb: k_+=1; inpb=True; newx=False
    f['e押し回数']=k_ if f['eMA向き'] else -1
    f['eMA20距離']=round(float((c-m20[-1])*s/A1[-1]),2); f['eMA75距離']=round(float((c-m75[-1])*s/A1[-1]),2)
    f['e75傾き']=round(float((m75[-1]-m75[-11])*s/A1[-1]),2)
    # impulse lines (H4, H1) touched in the last 48h, same direction
    tl=[]
    for tf,df,R,C,A in (('H4',F.h4,F.R4,F.C4,A4),('H1',F.h1,F.R1,F.C1,A1)):
        for x in EL.line_touches(df,R,C,A,tf):
            if x['kind']=='touch' and x['d']==want and pd.Timestamp(x['t'])>=t-pd.Timedelta('48h'): tl.append(f"{tf}{x['n']}点目")
    f['e推進']=','.join(sorted(set(tl)))
    # correction lines broken in the trade direction: M15 (EA-C lines) in last 8h, H1 version in last 24h
    L15,_=EC.lines(F)
    brk15=[x for x in L15 if x[7] and ((x[6]=='hi')==(s==1)) and F.T15[x[5]]>=t-pd.Timedelta('8h')]
    f['eM15逆トレ抜け']=len(brk15)>0
    S=Shim(); S.h,S.l,S.c=(h1[z].to_numpy(float) for z in 'hlc'); S.m15=h1; S.T15=pd.to_datetime(h1.t); S.R15=F.R1
    old=(EC.LOOK,EC.IMPW,EC.IMP); EC.LOOK,EC.IMPW,EC.IMP=20,48,5.0
    L1,_=EC.lines(S); EC.LOOK,EC.IMPW,EC.IMP=old
    brk1=[x for x in L1 if x[7] and ((x[6]=='hi')==(s==1)) and S.T15[x[5]]>=t-pd.Timedelta('24h')]
    f['eH1逆トレ抜け']=len(brk1)>0
    # M15 turn in the last 4h
    pv=[x for x in F.R15['prov_events'] if x['action'] in('REVERSAL','PROV_START') and x['to']==want]
    f['eM15転換']=bool(pv and F.T15[pv[-1]['idx']]>=t-pd.Timedelta('4h'))
    for col,k2 in [('水平線D1.H4','u水平線'),('トレンドライン（推進）','u推進'),('トレンドライン（逆トレ）','u逆トレ'),('トレンドライン（M15）','uM15'),('H1MAエリア','uH1MA'),('D1','uD1'),('H4','uH4'),('H1','uH1'),('DowRule','uDow')]:
        f[k2]=r[col]
    rows.append(f); print(sym, t, 'ok', flush=True)
pd.DataFrame(rows).to_pickle('audit.pkl'); print('done',len(rows))
