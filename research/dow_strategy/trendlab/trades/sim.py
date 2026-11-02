"""User's real trades re-run on price data: actual exit vs mechanical exits, with the EA's own swings / Dow (causal)."""
import sys, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from env_recognition.pivots import atr
e=pd.read_pickle('/home/user/sheet/entries_clean.pkl'); e['pair']=e['PairName（元）'].replace({'CHEJPY':'CHFJPY'})
HAVE=['EURUSD','GBPUSD','AUDUSD','USDCAD','USDCHF','USDJPY','EURJPY','AUDJPY','CADJPY','CHFJPY','XAUUSD','US500','JP225','OIL','NGAS']
e=e[e.pair.isin(HAVE)&e.EntryTime.notna()&e.sl.notna()&(e.sl>0)].copy()
PIPC={'XAUUSD':[0.01,0.1,1],'JP225':[0.1,1,10],'US500':[0.01,0.1,1],'OIL':[0.001,0.01,0.1],'NGAS':[0.001,0.01]}
def pipof(s): return [0.01] if s.endswith('JPY') else PIPC.get(s,[0.0001])
M={}
def m15(sym):
    if sym not in M:
        M[sym]=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
    return M[sym]
def path_ok(H,L,i,s,en,sl,ex,win):
    for j in range(i,min(len(H),i+960)):
        if (L[j]<=sl) if s==1 else (H[j]>=sl): return not win, j
        if win and ((H[j]>=ex) if s==1 else (L[j]<=ex)): return True, j
    return False, None
rows=[]
for _,r in e.iterrows():
    sym=r.pair; s=1 if r.Direction=='Buy' else -1
    tj=pd.Timestamp(r.EntryDate.date())+pd.Timedelta(str(r.EntryTime)); tb=tj-pd.Timedelta(hours=6 if 4<=tj.month<=10 else 7)
    m=m15(sym); T=m.t; i=int(T.searchsorted(tb)); 
    if i+10>=len(m): continue
    H,L,C,O=(m[z].to_numpy(float) for z in 'hlcO'.lower()) if False else (m.h.to_numpy(float),m.l.to_numpy(float),m.c.to_numpy(float),m.o.to_numpy(float))
    win=r.pips>0
    best=None
    for pip in pipof(sym):
        en=float(r.EntryPrice) if pd.notna(r.EntryPrice) else O[i]
        sl=float(r.InitialSLPrice) if pd.notna(r.InitialSLPrice) else en-s*r.sl*pip
        ex=float(r.ExitPrice) if pd.notna(r.ExitPrice) else en+s*r.pips*pip
        ok,j=path_ok(H,L,i,s,en,sl,ex,win)
        if r.pips<=0 and r.pips>-r.sl: ok,j=True,None    # cut early / break-even: exit time unknown
        if ok and best is None: best=(pip,en,sl,ex,j)
    if best is None: best=(pipof(sym)[min(1,len(pipof(sym))-1)],O[i],None,None,None); flag='価格が合わない'
    else: flag=''
    pip,en,sl,ex,j=best
    if sl is None: sl=en-s*r.sl*pip; ex=en+s*r.pips*pip
    rows.append(dict(id=r.EntryID,sym=sym,s=s,tj=tj,tb=tb,i=i,pip=pip,en=en,sl=sl,ex=ex,ex_j=j,R=r.pips/r.sl,win=r['勝敗'],flag=flag,
                     exit_t=(pd.Timestamp(r.ExitDate.date())+pd.Timedelta(str(r.ExitTime))) if pd.notna(r.ExitDate) and pd.notna(r.ExitTime) else pd.NaT))
X=pd.DataFrame(rows); X.to_pickle('trades.pkl'); print(len(X), X.flag.value_counts().to_dict(), X.groupby('sym').pip.first().to_dict())
