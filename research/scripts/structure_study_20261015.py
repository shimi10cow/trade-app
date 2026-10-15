import pandas as pd,numpy as np,zipfile
from pathlib import Path
out=Path('/mnt/data/ea_research')
out.mkdir(parents=True,exist_ok=True)
p='/mnt/data/EURUSD2003.M1.zip'
chunks=[]
with zipfile.ZipFile(p) as z:
 with z.open(z.namelist()[0]) as f:
  for c in pd.read_csv(f,chunksize=500000):
   dt=pd.to_datetime(c['<DTYYYYMMDD>'].astype(str)+c['<TIME>'].astype(str).str.zfill(4),format='%Y%m%d%H%M',errors='coerce')
   x=c[['<OPEN>','<HIGH>','<LOW>','<CLOSE>']].copy();x.columns=['open','high','low','close'];x.index=dt
   chunks.append(x.resample('1h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna())
h=pd.concat(chunks).sort_index();h=h.groupby(level=0).agg({'open':'first','high':'max','low':'min','close':'last'})
h4=h.resample('4h').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna()
hi=h4.high.to_numpy();lo=h4.low.to_numpy();idx=h4.index
is_hi=np.zeros(len(h4),bool);is_lo=is_hi.copy()
for k in (1,2):
 if k==1:
  is_hi[2:-2]=(hi[2:-2]>hi[1:-3])&(hi[2:-2]>hi[3:-1]);is_lo[2:-2]=(lo[2:-2]<lo[1:-3])&(lo[2:-2]<lo[3:-1])
 else:
  is_hi[2:-2]&=(hi[2:-2]>hi[:-4])&(hi[2:-2]>hi[4:]);is_lo[2:-2]&=(lo[2:-2]<lo[:-4])&(lo[2:-2]<lo[4:])
piv=[]
for i in np.flatnonzero(is_hi|is_lo):
 if is_hi[i]:piv.append((idx[i],idx[i+2]+pd.Timedelta(hours=4),'high',hi[i]))
 if is_lo[i]:piv.append((idx[i],idx[i+2]+pd.Timedelta(hours=4),'low',lo[i]))
pd.DataFrame(piv,columns=['pivot_time','available_at','kind','price']).to_csv(out/'h4_confirmed_pivots.csv',index=False)
r=h4.high-h4.low;tr=pd.concat([r,(h4.high-h4.close.shift()).abs(),(h4.low-h4.close.shift()).abs()],axis=1).max(axis=1)
h4['atr14']=tr.rolling(14).mean();h4['range_atr']=r/h4.atr14;h4['body_fraction']=(h4.close-h4.open).abs()/r.replace(0,np.nan)
h4['direction']=np.sign(h4.close-h4.open)
h4['rolling_20_range_atr']=(h4.high.rolling(20).max()-h4.low.rolling(20).min())/h4.atr14
h4.to_csv(out/'h4_structure_bars.csv')
y=h4.groupby(h4.index.year).agg(bars=('close','size'),median_bar_range_atr=('range_atr','median'),median_20bar_range_atr=('rolling_20_range_atr','median'))
y.to_csv(out/'h4_annual_structure_summary.csv')
print('H1 bars',len(h),'H4 bars',len(h4),'confirmed H4 pivots',len(piv));print(y.tail())
