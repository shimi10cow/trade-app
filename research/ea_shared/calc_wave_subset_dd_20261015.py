import pandas as pd, numpy as np
from pathlib import Path
p=Path('/mnt/data/ea_shared'); d=pd.read_csv(p/'DD_causal_wave_maturity_trades.csv');d['time']=pd.to_datetime(d.time);d['exit_time']=pd.to_datetime(d.exit_time)
base=(d.h4_impulse_ratio>=.70)&(d.h1_impulse_ratio<.75)
rows=[]
for label,mask in [('H4 maintained + H1 contracted (359)',base),('Above + SMA480 distance <12 ATR (284)',base&(d.d480<12))]:
 x=d.loc[mask].copy().sort_values(['exit_time','time']); r=x.R.to_numpy();eq=np.r_[0,np.cumsum(r)];peak=np.maximum.accumulate(eq);dd=eq-peak;idx=dd.argmin();peakidx=np.argmax(eq[:idx+1]);wins=(r>0).sum();loss=(r<0).sum();zero=(r==0).sum(); pos=r[r>0].sum();neg=-r[r<0].sum();annual=x.groupby(x.time.dt.year).R.agg(['size','sum']); annual.columns=['trades','sumR']; annual.to_csv(p/('DD_wave_annual_359.csv' if len(x)==359 else 'DD_wave_annual_284.csv'))
 print('\n',label,'n',len(x),'W/L/Z',wins,loss,zero,'sum',r.sum(),'PF',pos/neg,'maxDD',dd.min(),'peak',x.iloc[peakidx-1].exit_time if peakidx>0 else 'start','trough',x.iloc[idx-1].exit_time if idx>0 else 'start','avgwin',r[r>0].mean(),'avgloss',r[r<0].mean(),'maxwin',r.max(),'maxloss',r.min(),'longestloss',max(map(len,''.join('L' if a<0 else 'W' for a in r).split('W'))),'activeyears',annual.shape[0],'maxannual',annual['sumR'].max(),'minannual',annual['sumR'].min());
 rows.append(dict(condition=label,n=len(x),wins=int(wins),losses=int(loss),breakeven=int(zero),winrate=wins/len(x),sumR=r.sum(),PF=pos/neg,avgR=r.mean(),avgWinR=r[r>0].mean(),avgLossR=r[r<0].mean(),maxDD_closed_R=dd.min(),peak_date=str(x.iloc[peakidx-1].exit_time) if peakidx else 'initial',trough_date=str(x.iloc[idx-1].exit_time) if idx else 'initial',max_winR=r.max(),max_lossR=r.min(),longest_loss_streak=max(map(len,''.join('L' if a<0 else 'W' for a in r).split('W'))),yearly_avg_count=len(x)/24))
 x[['time','exit_time','point','side','R','d480','h4_impulse_ratio','h1_impulse_ratio']].to_csv(p/('DD_wave_trades_359.csv' if len(x)==359 else 'DD_wave_trades_284.csv'),index=False)
pd.DataFrame(rows).to_csv(p/'DD_wave_subset_performance_20261015.csv',index=False)
