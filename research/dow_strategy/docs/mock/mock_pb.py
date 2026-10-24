import pandas as pd, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
plt.rcParams['font.family']='IPAGothic'
S='/tmp/claude-0/-home-user-trade-app/dde437f2-70a2-5a18-92f1-b264add5082b/scratchpad'
m=pd.read_csv(f'{S}/EURUSD_M15_long_broker.csv',parse_dates=['time']).set_index('time')
h=m.loc['2010-06-01':'2010-07-20'].resample('1h').agg(dict(open='first',high='max',low='min',close='last')).dropna()
h4=m.loc['2010-05-01':'2010-07-20'].resample('4h').agg(dict(open='first',high='max',low='min',close='last')).dropna()
c=h.close; s20=c.rolling(20).mean(); s75=c.rolling(75).mean()
h=h.iloc[100:]; s20=s20.iloc[100:]; s75=s75.iloc[100:]; n=len(h); x=np.arange(n)
# swing lows (pullbacks): local minima over +-15 bars
lo=h.low.values; hi=h.high.values
piv=[i for i in range(15,n-15) if lo[i]==lo[i-15:i+16].min()]
fig=plt.figure(figsize=(15,9.2),dpi=110); ax=fig.add_axes([0.04,0.08,0.70,0.72])
for i,(o,hh,ll,cc) in enumerate(h[['open','high','low','close']].values):
    col='#1f8a4c' if cc>=o else '#c8372d'; ax.vlines(i,ll,hh,color=col,lw=.7); ax.add_patch(plt.Rectangle((i-.35,min(o,cc)),.7,max(abs(cc-o),1e-5),color=col))
ax.plot(x,s20.values,color='#0284c7',lw=1.2,label='SMA20'); ax.plot(x,s75.values,color='#b45309',lw=1.2,label='SMA75')
ax.set_xlim(-2,n+2); ax.legend(loc='lower right',fontsize=9)
ticks=list(range(0,n,48)); ax.set_xticks(ticks); ax.set_xticklabels([h.index[i].strftime('%m/%d') for i in ticks],fontsize=9)
ax.grid(alpha=.25)
def low_in(d0,d1):
    w=h.loc[d0:d1]; t=w.low.idxmin(); return h.index.get_loc(t)
def lab(i,y,t,solid=True,col='#2457c5'):
    ax.annotate(t,(i,y),ha='center',va='center',fontsize=12,color='white' if solid else col,
      bbox=dict(boxstyle='round,pad=0.3',fc=col if solid else 'white',ec=col,lw=1.6,ls='-' if solid else '--'))
rng=(h.high.max()-h.low.min())
B=h.index.get_loc(h.loc['2010-06-09 06:00':'2010-06-09 23:00'].close.idxmax())
P1=low_in('2010-06-16','2010-06-18'); P2=low_in('2010-06-28','2010-06-30'); P3=low_in('2010-07-12','2010-07-14'); G=low_in('2010-06-22','2010-06-24')
ax.axvline(B,color='#7c3aed',ls=':',lw=1.2); lab(B,lo[B]-rng*.06,'B 上昇',True,'#7c3aed')
for k,p in enumerate((P1,P2,P3)): lab(p,lo[p]-rng*.05,f'{k+1}回目',True,'#2457c5')
lab(P1,lo[P1]-rng*.115,'自動 1',False,'#64748b'); lab(G,lo[G]-rng*.07,'自動 2',False,'#64748b'); lab(P2,lo[P2]-rng*.115,'自動 3',False,'#64748b'); lab(P3,lo[P3]-rng*.115,'自動 4',False,'#64748b')
ax.annotate('',xy=(P3+3,lo[P3]-rng*.05),xytext=(P3+30,lo[P3]-rng*.02),arrowprops=dict(arrowstyle='->',color='#ea580c',lw=1.5))
ax.text(P3+31,lo[P3]-rng*.02,'掴んで動かせる',color='#ea580c',fontsize=10,va='center')
ax.axvspan(B,P1,color='#7c3aed',alpha=.06); ax.text((B+P1)/2,h.high.iloc[B:P1+1].max()+rng*.03,'B〜1回目の途中\n（ここで入るのもあり）',ha='center',fontsize=9.5,color='#7c3aed')
ax.set_ylim(h.low.min()-rng*.16,h.high.max()+rng*.08)
# toolbar mock
fa=fig.add_axes([0.04,0.83,0.92,0.15]); fa.axis('off'); fa.set_xlim(0,100); fa.set_ylim(0,10)
def btn(x0,y0,t,on=False,w=None,col='#2457c5'):
    w=w or len(t)*1.45+2.2; fa.add_patch(FancyBboxPatch((x0,y0),w,2.8,boxstyle='round,pad=0.2',fc=col if on else 'white',ec=col if on else '#94a3b8',lw=1.2))
    fa.text(x0+w/2,y0+1.4,t,ha='center',va='center',fontsize=11,color='white' if on else '#0f172a',fontweight='bold' if on else 'normal'); return x0+w+1.2
fa.text(0,8.6,'モード：',fontsize=12,fontweight='bold',va='center')
xx=7
for t,on in (('押し目カウント',True),('ダウ',False),('水平線',False),('トレンドライン',False),('ふだんの表示',False)): xx=btn(xx,7.2,t,on)
fa.text(0,3.6,'置く：',fontsize=12,fontweight='bold',va='center')
xx=7
for t,on,col in (('上昇 B',False,'#7c3aed'),('下降 B',False,'#7c3aed'),('次の番号（今：3）',True,'#2457c5'),('R レンジ入り',False,'#64748b')): xx=btn(xx,2.2,t,on,col=col)
fa.text(xx+1,3.6,'足：[ H4 ][ H1 ][ M15 ]　 自動の数え方：[表示]　 ほかの足で置いたラベル：[小さく表示]',fontsize=10.5,va='center',color='#334155')
# side panel
sp=fig.add_axes([0.76,0.08,0.22,0.72]); sp.axis('off'); sp.set_xlim(0,10); sp.set_ylim(0,20)
sp.add_patch(FancyBboxPatch((0,0),10,20,boxstyle='round,pad=0.1',fc='#f8fafc',ec='#cbd5e1'))
lines=[('この年に置いたラベル（H1）',True),(h.index[B].strftime('%m/%d %H:%M')+'  B 上昇',False),(h.index[P1].strftime('%m/%d %H:%M')+'  1回目',False),(h.index[P2].strftime('%m/%d %H:%M')+'  2回目',False),(h.index[P3].strftime('%m/%d %H:%M')+'  3回目',False),('',False),
       ('ほかの足のラベル',True),('H4：05/26 B 上昇 → 1回目 06/09',False),('（H4 に切り替えても H1 の',False),('　ラベルは小さく「H1:2」と出る）',False),('',False),
       ('自動の数え方との違い',True),('自動は '+h.index[G].strftime('%m/%d')+' の浅い押しも',False),('1回と数えていた（あなたは数えない）',False),('→ この差を集めて数え方を直す',False)]
y=19
for t,b in lines: sp.text(0.4,y,t,fontsize=10.5 if not b else 11,fontweight='bold' if b else 'normal',va='top'); y-=1.25
fig.text(0.04,0.025,'ユーロドル H1 2010年6月（実データ）。濃い色＝あなたが置いたラベル、点線＝自動の数え方。ラベルはタップで番号変更・削除、掴んで移動。リプレイ中でも置ける。',fontsize=10.5,color='#334155')
out='/home/user/trade-app/research/dow_strategy/docs/mock/pullback_mode_mock.png'; fig.savefig(out); print(out)
