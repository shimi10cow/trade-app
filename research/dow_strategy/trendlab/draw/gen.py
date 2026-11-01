import sys, json, numpy as np, pandas as pd
sys.path.insert(0,'/home/user/trade-app/research'); sys.path.insert(0,'/home/user/trade-app')
from mt5_ea.live.core import Frames
from mt5_ea.live.eas import l as EL, c as EC
from env_recognition.pivots import atr
EL.ULOOK['D1']=20
exec(open('/home/user/trendlab/audit/audit.py').read().split('class Shim')[0].split('LOGS=')[1].join(['LOGS=','']) if False else '')
LOGS={'XAUUSD','US500','JP225'}
A=pd.read_pickle('/home/user/trendlab/audit/audit.pkl')
M={}
def m15(sym):
    if sym not in M:
        m=pd.read_pickle(f'/home/user/trendlab/stoch/m15_{sym}.pkl').rename(columns=dict(time='t',open='o',high='h',low='l',close='c'))
        if sym in LOGS:
            for z in 'ohlc': m[z]=np.log(m[z])
        if sym.endswith('JPY'):
            for z in 'ohlc': m[z]=m[z]/100
        M[sym]=m
    return M[sym]
def back(sym,v):
    v=np.asarray(v,float)
    if sym in LOGS: return np.exp(v)
    if sym.endswith('JPY'): return v*100
    return v
class Shim: pass
out=[]
for n,r in A.iterrows():
    sym=r.sym; s=r.s; t=r.tb; want='up' if s==1 else 'down'
    m=m15(sym); w=m[(m.t>=t-pd.Timedelta(days=440))&(m.t<t)].reset_index(drop=True)
    F=Frames(w,t-pd.Timedelta(days=2))
    px=float(back(sym,F.c[-1])); dg=max(0,5-int(np.floor(np.log10(abs(px))))-1)
    q=lambda v:[round(float(z),dg) for z in back(sym,v)]
    item=dict(id=str(r.id),sym=sym,s=int(s),tj=r.tj.strftime('%Y-%m-%d %H:%M'),win=str(r.win),d=dg,
              user=dict(水平線=str(r.u水平線),推進=str(r.u推進),逆トレ=str(r.u逆トレ),M15=str(r.uM15),H1MA=str(r.uH1MA)))
    A4=atr(F.h4); A1=atr(F.h1)
    panels={}
    for tf,df,N in (('H4',F.h4,120),('H1',F.h1,160),('M15',F.m15.rename(columns={}),192)):
        df=df.reset_index(drop=True); a=max(0,len(df)-N); sl=df.iloc[a:]
        p=dict(o=q(sl.o),h=q(sl.h),l=q(sl.l),c=q(sl.c),tt=[x.strftime('%m/%d %H:%M') for x in pd.to_datetime(sl.t)],a=a,lines=[],levels=[])
        if tf=='H1':
            cc=df.c; p['m20']=q(cc.rolling(20).mean().iloc[a:].bfill()); p['m75']=q(cc.rolling(75).mean().iloc[a:].bfill())
        panels[tf]=p
    # EA levels (H4)
    k=len(F.h4)-1; bars4=F.R4['bars']; lv=[]
    if bars4[k][0]==want and bars4[k][1] is not None: lv.append(('砦',bars4[k][1]))
    rev=[x for x in F.R4['events'] if x.get('machine')=='major' and x['action']=='REVERSAL']
    if rev and rev[-1]['to']==want: lv.append(('出入口',rev[-1]['broken_price']))
    for x in [x for x in F.R4['pivot_events'] if x['action']=='confirm' and x['kind']==('lo' if s==1 else 'hi')][-3:]: lv.append(('H4山谷',x['price']))
    for tf in ('H4','H1','M15'): panels[tf]['levels']=[[nm,round(float(back(sym,v)),dg)] for nm,v in lv]
    # EA impulse lines (H4, H1): every touch event in the shown window, drawn from A to the touch
    for tf,df,R,C,A_ in (('H4',F.h4,F.R4,F.C4,A4),('H1',F.h1,F.R1,F.C1,A1)):
        a=panels[tf]['a']; Cs=pd.Series(pd.to_datetime(C))
        seen=set()
        for x in EL.line_touches(df,R,C,A_,tf):
            if x['kind']!='touch': continue
            j=int(Cs.searchsorted(pd.Timestamp(x['t'])))
            if j<a or (x['ia'],x['d']) in seen: continue
            seen.add((x['ia'],x['d']))
            pa=df.l.iat[x['ia']] if x['d']=='up' else df.h.iat[x['ia']]
            panels[tf]['lines'].append(['推進',x['ia']-a,round(float(back(sym,pa)),dg),j-a,round(float(back(sym,x['v'])),dg),x['d']==want])
    # EA correction lines: M15 (EA-C) and the same recipe on H1
    L15,_=EC.lines(F); a=panels['M15']['a']; n15=len(F.m15)
    for ia,pa,ib,pb,cr,end,kind,broken in L15:
        e_=end if end is not None else n15-1
        if e_<a: continue
        sl=(pb-pa)/(ib-ia); panels['M15']['lines'].append(['逆トレ',ia-a,round(float(back(sym,pa)),dg),e_-a,round(float(back(sym,pa+sl*(e_-ia))),dg),bool(broken)])
    S=Shim(); h1=F.h1; S.h,S.l,S.c=(h1[z].to_numpy(float) for z in 'hlc'); S.m15=h1; S.T15=pd.to_datetime(h1.t); S.R15=F.R1
    old=(EC.LOOK,EC.IMPW,EC.IMP); EC.LOOK,EC.IMPW,EC.IMP=20,48,5.0; L1,_=EC.lines(S); EC.LOOK,EC.IMPW,EC.IMP=old
    a=panels['H1']['a']; n1=len(h1)
    for ia,pa,ib,pb,cr,end,kind,broken in L1:
        e_=end if end is not None else n1-1
        if e_<a: continue
        sl=(pb-pa)/(ib-ia); panels['H1']['lines'].append(['逆トレ',ia-a,round(float(back(sym,pa)),dg),e_-a,round(float(back(sym,pa+sl*(e_-ia))),dg),bool(broken)])
    for p in panels.values():
        p['lines']=[l_ for l_ in p['lines'] if l_[3]>=0]
        for l_ in p['lines']:
            if l_[1]<0:   # clip start into view
                f=(0-l_[1])/((l_[3]-l_[1]) or 1); l_[2]=round(l_[2]+(l_[4]-l_[2])*f,dg); l_[1]=0
    item['P']=panels; out.append(item); print(n,sym,'ok',flush=True)
open('data.js','w').write('const DATA='+json.dumps(out,separators=(',',':'),ensure_ascii=False)+';')
import os; print(len(out),os.path.getsize('data.js'))
