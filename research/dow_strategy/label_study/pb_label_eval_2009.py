import json, numpy as np, pandas as pd
S='/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
D=pd.read_pickle(f'{S}/pbm_jpy.pkl').sort_values('t')
V=json.load(open(f'{S}/viewer_jpy/data/2009.json')); PBC=json.load(open(f'{S}/viewer_jpy/data/pbc.json'))
m=pd.read_csv(f'{S}/jpy/USDJPY_M15_long_broker.csv',parse_dates=['time']).set_index('time').loc['2008-10-01':'2009-09-30']
def bars(rule):
    b=m.resample(rule,label='left',closed='left').agg(dict(open='first',high='max',low='min',close='last')).dropna()
    pc=b.close.shift(); tr=np.maximum(b.high-b.low,np.maximum((b.high-pc).abs(),(b.low-pc).abs())); b['atr']=tr.rolling(14).mean()
    b['s20']=b.close.rolling(20).mean(); b['s75']=b.close.rolling(75).mean(); return b
B={'H1':bars('1h'),'H4':bars('4h')}
# sequences
def seq(tf):
    x=D[D.tf==tf].sort_values('t'); out=[]; side=0; n=0; on=False; legs=[]
    for r in x.itertuples():
        if r.kind=='B':
            if on: legs.append(n)
            side=r.side; n=0; on=True; out.append((r.t,'B',side,0,r.p))
        elif r.kind=='R':
            if on: legs.append(n)
            on=False; out.append((r.t,'R',0,0,r.p))
        elif on: n+=1; out.append((r.t,'N',side,n,r.p))
    if on: legs.append(n)
    return pd.DataFrame(out,columns=['t','k','side','n','p']),legs
print('### 1. ラベルの数と、1つのトレンドで何回押したか')
for tf in ('H4','H1'):
    s,legs=seq(tf); c=pd.Series(legs).value_counts().sort_index()
    print(tf,'B',(s.k=='B').sum(),'回、押し',(s.k=='N').sum(),'個。トレンド1本あたりの押しの数の分布:',dict(c), ' 平均',round(np.mean(legs),2))
# 2. B vs mechanical: H1/H4 major Dow reversals (ev 'rev'), provisional turns (pev), SMA20/75 cross
print('\n### 2. あなたの B と機械的な合図の時間差（B − 合図、時間。マイナス＝あなたの方が早い）')
for tf in ('H4','H1'):
    s,_=seq(tf); L=3600 if tf=='H1' else 14400; b=B[tf]
    rev=[(e[0],1 if e[2]=='up' else -1) for e in V[tf]['ev'] if e[1]=='rev']
    pev=[(e[0],1 if e[1]=='up' else -1) for e in V[tf]['pev']]
    cr=np.sign(b.s20-b.s75); crx=[(int(t.timestamp()),int(v)) for t,v in cr[cr.diff().fillna(0)!=0].items() if v!=0]
    for nm,ev in (('本ダウ転換',rev),('仮ダウ転換',pev),('SMA20/75クロス',crx)):
        dl=[]
        for r in s[s.k=='B'].itertuples():
            c=[(t-r.t)/3600 for t,sd in ev if sd==r.side and abs(t-r.t)<=10*86400]
            if c: dl.append(min(c,key=abs))
        dl=np.array(dl)
        if len(dl): print(f'{tf} {nm:12s} 対応あり {len(dl)}/{(s.k=="B").sum()}  中央 {np.median(dl):+.0f}h  あなたが先 {(dl<0).mean():.0%}  ±12h以内 {(abs(dl)<=12).mean():.0%}')
# 3. pullback number vs auto counters
print('\n### 3. あなたの押しの番号と自動の数え方（MA基準／ダウ基準）')
for tf in ('H4','H1'):
    s,_=seq(tf); R=np.array(PBC[tf]); rows=[]
    for r in s[s.k=='N'].itertuples():
        j=np.searchsorted(R[:,0],r.t+(3600 if tf=='H1' else 14400),'right')-1
        if j<0: continue
        a=R[j]; ma=(a[2]+1) if a[1]==r.side else 0; dw=(a[4]+1) if a[3]==r.side else 0
        rows.append((min(r.n,4),min(ma,4),min(dw,4)))
    X=pd.DataFrame(rows,columns=['you','ma','dow'])
    print(tf,'一致率 MA',f"{(X.you==X.ma).mean():.0%}",'ダウ',f"{(X.you==X.dow).mean():.0%}",' 方向まで逆（自動は逆のトレンド） MA',f"{(X.ma==0).mean():.0%}",'ダウ',f"{(X.dow==0).mean():.0%}")
    print(pd.crosstab(X.you,X.ma,rownames=['あなた'],colnames=['MA基準（0=逆/なし）']).to_string())
# 4. forward: from each label, continuation (new extreme beyond the leg's high) before failure (1 ATR beyond the label)
print('\n### 4. ラベルのあと：トレンド方向に「直前の高値（安値）を更新」が先か、「ラベルから1ATR逆行」が先か')
for tf in ('H4','H1'):
    s,_=seq(tf); b=B[tf]; T=np.array([int(t.timestamp()) for t in b.index]); H=b.high.values; Lw=b.low.values; A=b.atr.values; rows=[]
    lastB=None
    for r in s.itertuples():
        if r.k=='B': lastB=r; 
        if r.k not in ('B','N') or lastB is None: continue
        i=np.searchsorted(T,r.t); 
        if i>=len(T)-2: continue
        sd=r.side; i0=np.searchsorted(T,lastB.t)
        ext=H[i0:i+1].max() if sd==1 else Lw[i0:i+1].min()
        stop=r.p-sd*A[i]; res=None
        for j in range(i+1,min(len(T),i+(120 if tf=='H1' else 60))):
            if (Lw[j]<=stop) if sd==1 else (H[j]>=stop): res=0;break
            if (H[j]>ext) if sd==1 else (Lw[j]<ext): res=1;break
        rows.append(('B' if r.k=='B' else str(min(r.n,4)),res))
    X=pd.DataFrame(rows,columns=['lab','ok'])
    g=X.groupby('lab').ok.agg(['mean','count']); print(tf); print(g.round(2).to_string())
