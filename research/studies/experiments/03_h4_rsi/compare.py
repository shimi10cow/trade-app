from pathlib import Path
import pandas as pd
ROOT=Path('/mnt/data/ea_cache')
OUT=Path(__file__).resolve().parent
OUT.mkdir(parents=True,exist_ok=True)
def load(suffix):
 p=ROOT/f'EURUSD_off_p12_{suffix}_exp03_trades.pkl'
 if not p.exists():raise SystemExit(f'Missing completed run: {p}')
 return pd.read_pickle(p)
a,b=load('none'),load('h4_rsi')
def metric(df):
 r=df['R'].astype(float) if 'R' in df else df['r'].astype(float)
 gain=r[r>0].sum(); loss=-r[r<0].sum()
 dd=(r.cumsum()-r.cumsum().cummax().clip(lower=0)).min()
 return {'trades':len(r),'total_R':round(r.sum(),4),'PF':round(gain/loss,4) if loss else None,'max_DD_R':round(dd,4),'win_rate':round((r>0).mean(),4) if len(r) else None}
rows=[]
for label,df in [('ON',a),('OFF',b)]:
 df=df.sort_values('time')
 for period,subset in [('all',df),('2015+',df[df.time>=pd.Timestamp('2015-01-01')])]:
  rows.append({'filter':label,'period':period,**metric(subset)})
 for y,g in df.groupby(df.time.dt.year):
  rows.append({'filter':label,'period':str(y),**metric(g)})
pd.DataFrame(rows).to_csv(OUT/'comparison.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
