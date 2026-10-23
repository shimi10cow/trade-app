"""Look-ahead check of entry prices (2026-10-23): for every adopted trade, is the entry the open of the bar after the signal
(or, for the R/T engine and RSI(2), the signal bar close), and did the stop sit inside the entry bar? Run from the scratchpad."""
import pandas as pd, numpy as np
S='.'
T=pd.concat([pd.read_pickle('feat/all_trades_xm.pkl'),pd.read_pickle('feat/all_trades_new.pkl')])
Q=pd.read_pickle('feat/q_best.pkl')[['R','tt','et','side','risk','entry','key','pair']]
T=pd.concat([T,Q]); T['tt']=pd.to_datetime(T.tt)
ADOPT={'R@EURUSD','T2@EURUSD','L@EURUSD','A@EURUSD','C@EURUSD','C@USDJPY','J2@USDJPY','L2@XAUUSD','S@XAUUSD','Q@XAUUSD','Q@XAGUSD','T@US30','Q@US30'}
T=T[T.key.isin(ADOPT)].drop_duplicates(['key','tt'])
rows=[]
for sym,g in T.groupby('pair'):
    f='EURUSD_M15_long_broker.csv' if sym=='EURUSD' else f'ws_{sym}/M15_broker.csv'
    m=pd.read_csv(f,parse_dates=['time']).set_index('time')
    for key,h in g.groupby('key'):
        o=m.open.reindex(h.tt).to_numpy(); hi=m.high.reindex(h.tt).to_numpy(); lo=m.low.reindex(h.tt).to_numpy()
        e=h.entry.to_numpy()
        # unit: compare entry with bar open (raw, /100 or log)
        for nm,fn in (('raw',lambda v:v),('/100',lambda v:v/100),('log',np.log)):
            if np.nanmedian(np.abs(fn(o)-e)/np.abs(e))<1e-3: break
        o,hi,lo=fn(o),fn(hi),fn(lo); s=h.side.to_numpy(); sl=e-s*h.risk.to_numpy()
        same=np.abs(o-e)<=np.abs(e)*2e-5
        hit=(lo<=sl)&(s==1) | (hi>=sl)&(s==-1)
        R=h.R.to_numpy()
        rows.append(dict(key=key,unit=nm,n=len(h),found=np.isfinite(o).mean(),entry_eq_open=np.nanmean(same),entry_bar_hits_stop=int(np.nansum(hit)),
                         R_of_those=R[hit].sum(),R_total=R.sum(),R_if_stopped=R.sum()-R[hit].sum()+(-1.0-0.02)*hit.sum()))
D=pd.DataFrame(rows).round(3); pd.set_option('display.width',200); print(D.to_string(index=False))
print('合計', D[['n','entry_bar_hits_stop','R_total','R_if_stopped']].sum().round(1).to_dict())
