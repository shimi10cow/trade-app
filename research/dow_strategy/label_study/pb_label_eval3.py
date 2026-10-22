exec(open('/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad/pbm_eval2.py').read().split("print('\\n### 2.")[0].replace("print(","(lambda *a,**k:None)("))
def cnt(tf,bt,side,t_eval,par,dmin):
    b=BR[tf]; T=TT[tf]; i0=np.searchsorted(T,bt); i1=np.searchsorted(T,t_eval,'right'); H=b.high.values; L=b.low.values; A=b.atr.values
    n=0; armed=True; ext=H[i0] if side==1 else L[i0]
    for j in range(i0+1,min(i1,len(T))):
        if (H[j]>ext) if side==1 else (L[j]<ext): ext=H[j] if side==1 else L[j]; newx=True
        else: newx=False
        k=j-par
        if k<=i0: continue
        w=L[max(i0,k-par):j+1] if side==1 else H[max(i0,k-par):j+1]
        piv=(L[k]==w.min()) if side==1 else (H[k]==w.max())
        deep=(ext-L[k] if side==1 else H[k]-ext)>=dmin*A[k]
        if armed and piv and deep: n+=1; armed=False
        if not armed and newx: armed=True
    return n
for tf in ('H4','H1'):
    rows=[]
    for per in ('2009','2013'):
        s,_=seq(tf,per)
        for r in s[s.k=='N'].itertuples():
            ev=r.t+(6 if tf=='H1' else 3)*(3600 if tf=='H1' else 14400)
            rows.append((per,r.n,{(p,dm):cnt(tf,r.bt,r.side,ev,p,dm) for p in (2,3,4) for dm in (0,0.5,1,1.5,2)}))
    out=[]
    for g in rows[0][2]:
        a=np.mean([min(n,4)==min(d[g],4) for per,n,d in rows]); a1=np.mean([min(n,4)==min(d[g],4) for per,n,d in rows if per=='2009']); a2=np.mean([min(n,4)==min(d[g],4) for per,n,d in rows if per=='2013'])
        w1=np.mean([abs(min(n,4)-min(d[g],4))<=1 for per,n,d in rows]); out.append((a,g,a1,a2,w1))
    out.sort(reverse=True)
    for a,g,a1,a2,w1 in out[:5]: print(f'{tf} スイング前後{g[0]}本 かつ 深さATR×{g[1]}以上：一致 {a:.0%}（2009 {a1:.0%}／2013 {a2:.0%}）、±1回以内 {w1:.0%}')
    best=out[0][1]; X=pd.DataFrame([(min(n,4),min(d[best],4)) for per,n,d in rows],columns=['you','auto'])
    print(pd.crosstab(X.you,X.auto,rownames=['あなた'],colnames=['自動']).to_string())
