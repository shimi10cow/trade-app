import sys,json,glob; sys.path.insert(0,'dow_strategy')
import numpy as np,pandas as pd
import triangles as TR
from portfolio import comp
J={(j['created'],j['shape']):j for j in (json.load(open(f)) for f in glob.glob(sys.argv[1]+'/*.json'))}
df,R=TR.FR['H4']; T=pd.to_datetime(df.t); sec=lambda t:int((t-pd.Timestamp('1970-01-01'))//pd.Timedelta(seconds=1))
tri=TR.detect2('H4'); out=TR.outcome('H4',tri)
out['key']=[(sec(T[x]),s) for x,s in zip(out.created,out['shape'])]
rows=[]
for x in tri:
    k=(sec(T[x['created']]),x['shape'])
    if k in J:
        o=out[out.key.apply(lambda z:z==k)]
        rows.append(dict(year=T[x['created']].year,shape=x['shape'],v=J[k].get('v'),fixed=any(f'f{p}_t' in J[k] for p in ('u0','uk','l0','lk')),
            w0=round(x['w0'],1),shrink=round(x['wk']/x['w0'],2),len=x['len'],wait=x['end']-x['created'],bo=x['bo'],
            f30=float(o.f30.iloc[0]) if len(o) else np.nan,with_higher=bool(o.with_higher.iloc[0]) if len(o) else None,
            t0=T[x['created']],te=T[x['end']]))
d=pd.DataFrame(rows); pd.set_option('display.width',200)
print(d.drop(columns=['t0','te']).to_string(index=False))
print(d.groupby('v')[['w0','shrink','len','wait','f30']].median().round(2)); print(d.v.value_counts().to_dict(),'動かした',int(d.fixed.sum()))
P=pd.concat([comp('R','regime_R1.csv'),comp('T','regime_T1.csv'),comp('L','tl_D2.csv'),comp('A','retest_E1.csv')])
for v in ('ok','×'):
    m=d[d.v=='ok'] if v=='ok' else d[d.v!='ok']
    hit=P[[any((a<=t<=b) for a,b in zip(m.t0,m.te)) for t in P.tt]]
    print(f'判定{v} の三角の最中に入った4本のトレード: {len(hit)}回 {hit._R.sum():+.1f}R')
