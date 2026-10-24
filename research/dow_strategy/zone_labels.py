import sys,json,glob,bisect; sys.path.insert(0,'dow_strategy')
import numpy as np,pandas as pd
import env_ctx as EC
from env_recognition import dow_trend
from portfolio import comp
h4=EC._h4; R4=dow_trend.run(h4,'H4'); C4=EC._C4; c=EC._cv; A=EC._A
s75=pd.Series(c).rolling(75).mean().to_numpy()
G=[json.load(open(f)) for f in glob.glob(sys.argv[1]+'/regime/*.json')]
P0=pd.concat([comp('R','regime_R1.csv'),comp('T','regime_T1.csv'),comp('L','tl_D2.csv'),comp('A','retest_E1.csv')])
pd.set_option('display.width',200)
ZK=('enter_buy','enter_sell','watch_buy','watch_sell','avoid')
for YR in [int(y) for y in sys.argv[2:]]:
    y0=pd.Timestamp(f'{YR}-01-01').value//10**9; y1=pd.Timestamp(f'{YR+1}-01-01').value//10**9
    Z=[g for g in G if g['kind'] in ZK and g['t2']>=y0 and g['t1']<y1]
    S=[g for g in G if g['kind'] not in ZK and g['t2']>=y0 and g['t1']<y1]
    print(f'##### {YR}: エリアの印 {len(Z)} 件 / 状態の印 {len(S)} 件')
    rows=[]
    for g in Z:
        t1=pd.Timestamp(g['t1'],unit='s'); k1=bisect.bisect_right(C4,t1)-1
        s=1 if g['kind'].endswith('buy') else -1 if g['kind'].endswith('sell') else 0
        fwd=lambda n: s*(c[min(len(c)-1,k1+n)]-c[k1])/A[k1] if s else abs(c[min(len(c)-1,k1+n)]-c[k1])/A[k1]
        rows.append(dict(kind=g['kind'],h4=R4['bars'][k1][0],adev=abs((c[k1]-s75[k1])/A[k1]),f20=fwd(20),f60=fwd(60),early=(s!=0 and R4['bars'][k1][0]!=('up' if s==1 else 'down'))))
    d=pd.DataFrame(rows)
    if len(d):
        print(d.groupby('kind').agg(n=('f20','size'),f20=('f20','median'),f60=('f60','median'),SMA75距離=('adev','median'),転換前に開始=('early','mean')).round(2))
    P=P0[P0.tt.dt.year==YR].copy()
    def zone(t,s):
        tt=t.value//10**9; hit=[g for g in Z if g['t1']<=tt<=g['t2']]
        if any(g['kind']==('enter_buy' if s==1 else 'enter_sell') for g in hit): return '入りたい（同じ向き）'
        if any(g['kind']==('watch_buy' if s==1 else 'watch_sell') for g in hit): return '検討中（同じ向き）'
        if any(g['kind'] in (('enter_sell','watch_sell') if s==1 else ('enter_buy','watch_buy')) for g in hit): return '逆向きのエリア'
        if any(g['kind']=='avoid' for g in hit): return '触りたくない'
        return 'エリア外'
    P['zone']=[zone(t,s) for t,s in zip(P.tt,P.side)]
    print(P.groupby('zone')._R.agg(['size','sum','mean']).round(2))
