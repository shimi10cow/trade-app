import json,re
from pathlib import Path
import pandas as pd
from dow_final_engine import calculate

B=Path('/mnt/data')
s=(B/'eurusd_dow_chart_demo_v14.html').read_text()
series=json.loads(re.search(r'const SERIES=(\{.*?\});',s,re.S).group(1))
labels=json.load(open(B/'eurusd_dow_annotations_v14 (1).json'))['swingByTF']
o=json.load(open(B/'eurusd_dow_zigzag_corrected_import.json'))
rows=[]
for tf in ['W1','D1','H4','H1','M15']:
    d=pd.DataFrame(series[tf]).iloc[:,:5]
    d.columns=['t','o','h','l','c']
    t=pd.to_datetime(d.t).astype('int64').to_numpy()//10**6
    ai=[int(abs(t-x['t']).argmin()) for x in labels[tf]]
    start=max(60,min(ai)-30); end=min(len(d)-1,max(ai)+30)
    pts=calculate(d,tf,start,end)
    o['swingByTF'][tf]=pts
    rows.append({'tf':tf,'candles':len(d),'range_start':str(d.t.iloc[start]),
                 'range_end':str(d.t.iloc[end]),'points':len(pts),
                 'highs':sum(x['kind']=='hi' for x in pts),
                 'lows':sum(x['kind']=='lo' for x in pts),
                 'same_type_adjacent':sum(pts[i]['kind']==pts[i-1]['kind'] for i in range(1,len(pts)))})
o['datasetId']='eurusd-dow-final-relocate-20261017'
o['view']['tf']='M15'
o['exportNote']='Relocation ON all TFs; ATR inflation cap OFF; retrospective pivots may repaint'
o['reviewByTF']={}; o['objects']=[]
o['seqByTF']={tf:(v[-1]['kind'] if v else None) for tf,v in o['swingByTF'].items()}
(B/'eurusd_dow_final_relocate_import.json').write_text(json.dumps(o,ensure_ascii=False))
pd.DataFrame(rows).to_csv(B/'dow_final_counts.csv',index=False)
print(pd.DataFrame(rows).to_string(index=False))
