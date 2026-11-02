"""App 'combination results' recomputed (2026-11-xx): live-code trades (gates on), + P, same method as research small_acct.py."""
import sys, numpy as np, pandas as pd, glob
sys.path.insert(0,'/home/user/trade-app'); sys.path.insert(0,'.')
import h4f
from mt5_ea.live.sizing import calendar_mult
P=pd.concat([pd.read_pickle(f) for f in glob.glob('port/p_*.pkl') if 'h4' not in f],ignore_index=True)
P=P[P.t>='2005-06-01']
G={'C@USDJPY':'open','T@US30':'open','Q@XAGUSD':'open','Q@US30':'open','DS@JP225':'open','R@EURUSD':'slope'}
keep=[]
for k,g in P.groupby('key'):
    if k in G:
        g=h4f.add(g.copy(),'t'); g=g[g['H4開き']<2.5] if G[k]=='open' else g[g['H4MA75傾き']<0.35]
    keep.append(g[['key','sym','t','exit_t','R','side']])
for s in ['XAUUSD','EURUSD','USDJPY']:
    d=pd.read_pickle(f'parity_nt_{s}.pkl')['mine']; d=d[d.R.notna()&d.exit_t.notna()&(d.t>='2005-06-01')]
    d=d[~d.get('open_end',pd.Series(False,index=d.index)).fillna(False).astype(bool)]
    keep.append(pd.DataFrame(dict(key=f'P@{s}',sym=s,t=pd.to_datetime(d.t),exit_t=pd.to_datetime(d.exit_t),R=d.R.astype(float),side=d.side.astype(int))))
X=pd.concat(keep,ignore_index=True); X['et']=pd.to_datetime(X.exit_t); X=X.dropna(subset=['et','R'])
days={}
for s in X.sym.unique():
    m=pd.read_pickle(f'stoch/m15_{s}.pkl'); dd=pd.DatetimeIndex(m.time.dt.normalize().unique())
    days[s]=pd.Series(1,index=dd).groupby([dd.year,dd.month]).cumsum()
def tdm(s,t):
    d=pd.Timestamp(t).normalize(); ser=days[s]; i=ser.index.searchsorted(d,side='right')-1
    return int(ser.iloc[i]) if i>=0 and ser.index[i].month==d.month and ser.index[i].year==d.year else 1
X['mult']=[calendar_mult(s,sd,t,tdm(s,t)) for s,sd,t in zip(X.sym,X.side,X.t)]
def sim(d,risk=0.01,half=True,wt=None):
    d=d.sort_values('et'); eq=pk=1.0; mdd=0.0
    w=d.key.map(wt or {}).fillna(1.0).to_numpy()
    for R,k,ww in zip(d.R.to_numpy(),d.mult.to_numpy(),w):
        eq*=1+risk*k*ww*(0.5 if (half and eq<0.9*pk) else 1.0)*R; pk=max(pk,eq); mdd=min(mdd,eq/pk-1)
    yrs=(d.et.max()-d.et.min()).days/365.25
    return eq**(1/yrs)-1, mdd, len(d)/yrs
HALF={'S@XAUUSD':0.5,'Q@XAUUSD':0.5}
NEED={'J2@USDJPY':7.4e4,'C@USDJPY':7.4e4,'R@EURUSD':7.4e4,'T2@EURUSD':7.4e4,'L@EURUSD':7.4e4,'A@EURUSD':7.4e4,'C@EURUSD':7.4e4,
 'DS@JP225':1.5e4,'S@BTCUSD':19.4e4,'DS@US500':24.4e4,'M@US500':32.6e4,'T@US30':39e4,'L2@XAUUSD':49.2e4,
 'DS@XAUUSD':54.4e4,'Q@XAGUSD':56.7e4,'Q@US30':57.9e4,'S@XAUUSD':79.6e4,'Q@XAUUSD':86.4e4,'M@US30':207.6e4}
# P: median min-lot risk at prices of 2026-10-24 (as §102), 1 USD = 158.5 JPY
px={}
for s in ['XAUUSD','EURUSD','USDJPY']:
    m=pd.read_pickle(f'stoch/m15_{s}.pkl'); m=m[m.time<='2026-10-24']; px[s]=m.close.iat[-1]
for s in ['XAUUSD','EURUSD','USDJPY']:
    d=pd.read_pickle(f'parity_nt_{s}.pkl')['mine']; r=d.risk.median()
    if s=='XAUUSD': usd=r*np.exp(px[s]); jpy=usd*158.5; width=f'約 {usd:.0f} ドル（{r*100:.2f}%）'
    elif s=='EURUSD': jpy=r*1000*158.5; width=f'約 {r*1e4:.0f} pips'
    else: jpy=r*100*1000; width=f'約 {r*1e4:.0f} pips'
    NEED[f'P@{s}']=jpy/0.01; print(f'P@{s}: min-lot loss {jpy:,.0f} JPY, stop {width}, need {jpy/0.01/1e4:.1f} 万円')
miss=set(X.key)-set(NEED); assert not miss,miss
prev=0
for cap in (20e4,30e4,50e4,60e4,100e4,300e4):
    ks=[k for k,v in NEED.items() if v<=cap]; d=X[X.key.isin(ks)]
    c,dd,n=sim(d,wt=HALF); add=[k for k in ks if NEED[k]>prev]; prev=cap
    print(f'{cap/1e4:.0f}万円 {len(ks)}本 年利 {c:+.0%} DD {dd:.0%} 年{n:.0f}回  +{add}')
for lab,kw in [('全部 S/Q半分 1%',dict(wt=HALF)),('全部 S/Q全量 1%',dict()),('全部 S/Q半分 0.75%',dict(risk=0.0075,wt=HALF)),('全部 S/Q全量 0.75%',dict(risk=0.0075)),
               ('全部 S/Q半分 1% 半分ルールなし',dict(wt=HALF,half=False)),('全部 S/Q半分 1% 暦なし',dict(wt=HALF))]:
    d=X.copy()
    if '暦なし' in lab: d['mult']=1.0
    c,dd,n=sim(d,**kw); print(f'{lab}: 年利 {c:+.0%} DD {dd:.0%} 年{n:.0f}回')
d=X[~X.key.str.startswith('P@')]; c,dd,n=sim(d,wt=HALF); print(f'19本（開き入り・P なし）1%: 年利 {c:+.0%} DD {dd:.0%} 年{n:.0f}回')
