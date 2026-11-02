"""Original stochastic EA (engine_m15) on one instrument under several configs; new filter = daily side (H4 SMA1200) and
H1 MA75 slope (10 bars) in the trade direction, both from bars closed before the signal."""
import sys, os, copy, numpy as np, pandas as pd
sym, conf = sys.argv[1], sys.argv[2]
cache=f'/home/user/trendlab/stoch/m15_{sym}.pkl'; os.environ['EA_M15_CACHE']=cache
sys.path.insert(0,'/home/user/trade-app/research/core')
import engine_m15 as EM
LOGS=('XAUUSD','US500','JP225')
m=pd.read_pickle(cache)      # gold / indices are already natural log in this cache (stoch/run.py)
d=m.set_index('time')
h1=d.resample('1h',label='left',closed='left').agg(dict(open='first',high='max',low='min',close='last')).dropna()
h4=d.resample('4h',label='left',closed='left').agg(dict(open='first',high='max',low='min',close='last')).dropna()
pc=h1.close.shift(); tr=np.maximum(h1.high-h1.low,np.maximum((h1.high-pc).abs(),(h1.low-pc).abs())); a1=tr.ewm(alpha=1/7,adjust=False).mean()
sl75=((h1.close.rolling(75).mean()-h1.close.rolling(75).mean().shift(10))/a1).to_numpy(); C1=(h1.index+pd.Timedelta('1h')).to_numpy()
side_d=np.sign(h4.close-h4.close.rolling(1200).mean()).to_numpy(); C4=(h4.index+pd.Timedelta('4h')).to_numpy()
def newf(t,side):
    t=np.datetime64(pd.Timestamp(t)); k1=np.searchsorted(C1,t,side='right')-1; k4=np.searchsorted(C4,t,side='right')-1
    if k1<0 or k4<0 or not np.isfinite(sl75[k1]) or not np.isfinite(side_d[k4]): return False
    return side_d[k4]==side and sl75[k1]*side>0
CONF={
 'orig':dict(), 'new':dict(extra_filter=newf),
 'new-傾き200':dict(extra_filter=newf,s200_min=-1e9),
 'new-200/480':dict(extra_filter=newf,ma200_480_tol_atr=1e9),
 'new-q75':dict(extra_filter=newf,q75_warmup=10**9),
 'new-ABCD':dict(extra_filter=newf,_noabcd=True),
 'new-長期MA全部':dict(extra_filter=newf,use_long_ma=False),
 'new-P1のみ':dict(extra_filter=newf,max_entry_point=1),
 'new-P1〜3':dict(extra_filter=newf,max_entry_point=3),
 'new-同時1':dict(extra_filter=newf,max_positions=1),
 'new-同時3':dict(extra_filter=newf,max_positions=3),
 'new-追従すぐ':dict(extra_filter=newf,use_delayed_zz=False),
}
kw=dict(CONF[conf]); noabcd=kw.pop('_noabcd',False)
if noabcd: EM.ma_abcd_reject=lambda r,side: False
cfg=copy.deepcopy(EM.CFG)
for k,v in kw.items(): setattr(cfg,k,v)
tr=EM.run_pair(sym,cfg)
tr=pd.DataFrame(tr); tr['sym']=sym; tr['conf']=conf
tr.to_pickle(f'/home/user/trendlab/sx/t_{sym}_{conf.replace('/','_')}.pkl'); print('done',sym,conf,len(tr),flush=True)
