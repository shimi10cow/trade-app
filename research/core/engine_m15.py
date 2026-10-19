"""Canonical FX EA full backtest engine v1.0 (reconstructed 2026-09-23).

This is the first version intended to regenerate signals from M15, rather than post-process
an old trade list.  It implements the rules explicitly agreed in the conversation.

One frozen cache is intentionally used: h4ext_<PAIR>_levels.csv. Those files are a pure
price-derived H4 structural-level indicator produced during the earlier work, and their exact
historical structure-construction semantics were not fully preserved in prose. Keeping the
cache prevents silently inventing a different structure algorithm. All entry timing, Stochastic,
P numbering, q75, MA filters, H1 inverse-trend logic, RSI state, position limits and exits are
recomputed causally from M15.

Event conventions fixed in v1:
- Entry occurs at M15 close when signal completes.
- A newly opened position can be stopped from the NEXT M15 bar.
- Completed H1/H4 bar becomes usable only at the next period boundary.
- Existing SL hit is evaluated before +2R activation and before new ZZ pivot updates.
- New confirmed ZZ pivot becomes usable from the next M15 bar.
- q75 history is per pair+side and uses only prior qualifying strengths.
- H4 structural cache: level is eligible when active_time <= entry time < expiry_time.
  The cache's expiry_time encodes the first revisit/consumption.

Run: python full_backtest_engine_v1.py
Outputs canonical_full_v1_trades.csv and canonical_full_v1_summary.csv.
"""
from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path('/mnt/data')
PAIRS=['AUDUSD','EURJPY','EURUSD','GBPUSD','USDCAD','USDJPY']

@dataclass
class Config:
    stoch_n:int=14; stoch_k:int=3; stoch_d:int=5
    atr_n:int=14; zz_atr:float=1.5
    max_positions:int=2
    s200_min:float=0.0
    ma200_480_tol_atr:float=0.0
    q75_warmup:int=100
    p3_mfe_atr:float=1.5
    h4_level_tol_atr:float=0.60
    delayed_zz_hours:int=240
    expansion_hours:int=24
    expansion_atr:float=0.50
    use_expansion_exception:bool=False
    use_delayed_zz:bool=True
    p_count_mode:str='signal' # preserve original P numbering
    use_h4_levels:bool=False
    use_h4_rsi:bool=False
    use_inverse_trend:bool=False
    max_entry_point:int=2
    extra_filter:object=None   # optional callable(time, side) -> bool; None keeps the canonical behaviour
    tp_fn:object=None          # optional callable(time, side, entry, risk) -> take-profit price or None
    tp_half:bool=False         # True: close half at TP and let the rest trail (default: close all)
CFG=Config()

def load_m15(pair):
    """Load a pre-existing M15 pickle or CSV. Never regenerate M1 here."""
    import os
    requested=os.environ.get("EA_M15_CACHE")
    candidates=([Path(requested)] if requested else [])+[
        ROOT/"ea_shared"/f"{pair}2003_M15.pkl",
        ROOT/f"{pair}2003_M15_exp08.pkl",
        ROOT/f"{pair}2003_M15_exp06.pkl",
        ROOT/f"{pair}2003_M15.pkl",
        ROOT/f"{pair}_M15_MT5.csv",
        ROOT/f"{pair}2020.M15.csv",
    ]
    candidates+=sorted(ROOT.glob(f"**/{pair}*M15*.pkl"))
    candidates+=sorted(ROOT.glob(f"**/{pair}*M15*.csv"))
    for path in dict.fromkeys(candidates):
        if not path.is_file():continue
        if path.suffix.lower()==".pkl":d=pd.read_pickle(path)
        else:d=pd.read_csv(path)
        if not {"time","open","high","low","close"}<=set(d.columns):
            if {"<DTYYYYMMDD>","<TIME>","<OPEN>","<HIGH>","<LOW>","<CLOSE>"}<=set(d.columns):
                d["time"]=pd.to_datetime(d["<DTYYYYMMDD>"].astype(str)+d["<TIME>"].astype(str).str.zfill(4),format="%Y%m%d%H%M")
                d=d.rename(columns={"<OPEN>":"open","<HIGH>":"high","<LOW>":"low","<CLOSE>":"close"})
            elif {"<DATE>","<TIME>","<OPEN>","<HIGH>","<LOW>","<CLOSE>"}<=set(d.columns):
                d["time"]=pd.to_datetime(d["<DATE>"].astype(str)+" "+d["<TIME>"].astype(str))
                d=d.rename(columns={"<OPEN>":"open","<HIGH>":"high","<LOW>":"low","<CLOSE>":"close"})
            else:continue
        d=d[["time","open","high","low","close"]].copy()
        d["time"]=pd.to_datetime(d["time"])
        d=d.sort_values("time").drop_duplicates("time").reset_index(drop=True)
        if len(d)<1000:continue
        print(f"M15 cache: {path} ({len(d):,} bars)",flush=True)
        return d
    raise FileNotFoundError(f"No M15 cache for {pair}. Attach an existing pickle to /mnt/data or set EA_M15_CACHE. M1 rebuilding is intentionally disabled.")

def ATR(d,n=14):
    pc=d.close.shift(1)
    tr=pd.concat([(d.high-d.low),(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)
    return tr.rolling(n).mean()

def resample_ohlc(d,freq):
    x=d.set_index('time').resample(freq,label='left',closed='left').agg({'open':'first','high':'max','low':'min','close':'last'}).dropna().reset_index()
    delta=pd.Timedelta(freq)
    x['avail_time']=x.time+delta
    return x

def causal_pivots(d, atr_col='atr', mult=1.5, avail_col='time'):
    """Return confirmed alternating pivots. Same-bar new extreme cannot confirm reversal."""
    out=[]; mode=0; extreme=None; extreme_i=None
    for i,r in d.iterrows():
        a=r[atr_col]
        if not np.isfinite(a) or a<=0: continue
        h,l=float(r.high),float(r.low)
        if extreme is None:
            extreme=float(r.close); extreme_i=i; continue
        th=mult*a
        if mode==0:
            # bootstrap direction only after threshold move from running extreme
            if h>extreme: extreme=h; extreme_i=i
            elif l<extreme: extreme=l; extreme_i=i
            # bootstrap using recent range is intentionally conservative
            continue
        if mode==1: # seeking high, last pivot low
            old_ext=extreme
            if l <= old_ext-th:
                out.append({'kind':'H','price':old_ext,'pivot_i':extreme_i,'confirm_i':i,'confirm_time':r[avail_col]})
                mode=-1; extreme=l; extreme_i=i
            elif h>old_ext:
                extreme=h; extreme_i=i
        else: # seeking low
            old_ext=extreme
            if h >= old_ext+th:
                out.append({'kind':'L','price':old_ext,'pivot_i':extreme_i,'confirm_i':i,'confirm_time':r[avail_col]})
                mode=1; extreme=h; extreme_i=i
            elif l<old_ext:
                extreme=l; extreme_i=i
    return pd.DataFrame(out)

def causal_pivots_bootstrap(d, atr_col='atr', mult=1.5, avail_col='time'):
    """Practical causal ZZ bootstrap: establish first leg once price reverses threshold from an extreme."""
    out=[]; hi=lo=None; hii=loi=None; mode=0; extreme=None; extreme_i=None
    for i,r in d.iterrows():
        a=r[atr_col]
        if not np.isfinite(a) or a<=0: continue
        h,l=float(r.high),float(r.low); th=mult*a
        if mode==0:
            if hi is None: hi=h;lo=l;hii=loi=i;continue
            oldhi,oldlo=hi,lo
            # reversal is checked against pre-bar extremes
            if l <= oldhi-th:
                out.append({'kind':'H','price':oldhi,'pivot_i':hii,'confirm_i':i,'confirm_time':r[avail_col]})
                mode=-1; extreme=l; extreme_i=i; continue
            if h >= oldlo+th:
                out.append({'kind':'L','price':oldlo,'pivot_i':loi,'confirm_i':i,'confirm_time':r[avail_col]})
                mode=1; extreme=h; extreme_i=i; continue
            if h>hi:hi=h;hii=i
            if l<lo:lo=l;loi=i
        elif mode==1:
            old=extreme
            if l <= old-th:
                out.append({'kind':'H','price':old,'pivot_i':extreme_i,'confirm_i':i,'confirm_time':r[avail_col]})
                mode=-1; extreme=l; extreme_i=i
            elif h>old: extreme=h;extreme_i=i
        else:
            old=extreme
            if h >= old+th:
                out.append({'kind':'L','price':old,'pivot_i':extreme_i,'confirm_i':i,'confirm_time':r[avail_col]})
                mode=1; extreme=h; extreme_i=i
            elif l<old: extreme=l;extreme_i=i
    return pd.DataFrame(out)

def build_features(pair,cfg=CFG):
    m=load_m15(pair)
    m['atr']=ATR(m,cfg.atr_n); m['sma200']=m.close.rolling(200).mean()
    ll=m.low.rolling(cfg.stoch_n).min(); hh=m.high.rolling(cfg.stoch_n).max()
    rawk=100*(m.close-ll)/(hh-ll)
    m['K']=rawk.rolling(cfg.stoch_k).mean(); m['D']=m.K.rolling(cfg.stoch_d).mean()

    h1=resample_ohlc(m,'1h'); h1['atr']=ATR(h1,cfg.atr_n)
    for n in [20,75,200,480]: h1[f'sma{n}']=h1.close.rolling(n).mean()
    h1['s200']=h1.sma200/h1.sma200.shift(12)-1; h1['s480']=h1.sma480/h1.sma480.shift(12)-1
    h1['gap75_200']=h1.sma75-h1.sma200; h1['gap75_200_24']=h1.gap75_200.shift(24)
    diff=h1.sma20-h1.sma75; prev=diff.shift(1)
    h1['regside']=np.where(diff>0,1,np.where(diff<0,-1,0))
    h1['cross']=np.where((prev<=0)&(diff>0),1,np.where((prev>=0)&(diff<0),-1,0))
    h1['h1i']=np.arange(len(h1))
    h1p=causal_pivots_bootstrap(h1.assign(time=h1.avail_time),'atr',cfg.zz_atr,'time') if cfg.use_inverse_trend else pd.DataFrame()

    h4=resample_ohlc(m,'4h'); h4['atr']=ATR(h4,cfg.atr_n)
    delta=h4.close.diff(); gain=delta.clip(lower=0); loss=(-delta.clip(upper=0))
    # Wilder RSI
    ag=gain.ewm(alpha=1/14,adjust=False,min_periods=14).mean(); al=loss.ewm(alpha=1/14,adjust=False,min_periods=14).mean()
    h4['rsi']=100-100/(1+ag/al)
    h4['h4i']=np.arange(len(h4))

    # merge latest completed H1/H4 onto M15
    h1cols=['avail_time','h1i','atr','sma20','sma75','sma200','sma480','s200','s480','gap75_200','gap75_200_24','regside','cross']
    h4cols=['avail_time','h4i','atr','rsi']
    m=pd.merge_asof(m.sort_values('time'),h1[h1cols].sort_values('avail_time'),left_on='time',right_on='avail_time',direction='backward',suffixes=('','_h1'))
    m=m.rename(columns={'atr_h1':'h1_atr'})
    m=pd.merge_asof(m.sort_values('time'),h4[h4cols].sort_values('avail_time'),left_on='time',right_on='avail_time',direction='backward',suffixes=('','_h4'))
    m=m.rename(columns={'atr_h4':'h4_atr'})
    m15p=causal_pivots_bootstrap(m[['time','high','low','close','atr']].copy(),'atr',cfg.zz_atr,'time')
    return m,h1,h4,h1p,m15p

def load_levels(pair):
    p=ROOT/f'h4ext_{pair}_levels.csv'
    x=pd.read_csv(p)
    for c in ['created_time','active_time','expiry_time']: x[c]=pd.to_datetime(x[c])
    return x

def h4_rsi_allowed(side, rsi, state):
    # state is dict peak/bottom; causal state updated on each newly available H4 value outside this helper
    if side==1: return not state['buy_block']
    return not state['sell_block']

def update_rsi_state(rsi,state):
    if not np.isfinite(rsi): return
    if rsi>=80:
        if not state['buy_block']: state['buy_block']=True;state['peak']=rsi
        else: state['peak']=max(state['peak'],rsi)
    elif state['buy_block']:
        if state['peak']-rsi>=5: state['buy_block']=False;state['peak']=np.nan
    if rsi<=20:
        if not state['sell_block']: state['sell_block']=True;state['bottom']=rsi
        else: state['bottom']=min(state['bottom'],rsi)
    elif state['sell_block']:
        if rsi-state['bottom']>=5: state['sell_block']=False;state['bottom']=np.nan

def ma_relation_pass(r,side,cfg):
    if side==1: return (r.sma200-r.sma480)>=-cfg.ma200_480_tol_atr*r.h1_atr
    return (r.sma480-r.sma200)>=-cfg.ma200_480_tol_atr*r.h1_atr

def expansion_exception(r,side,cfg):
    if not cfg.use_expansion_exception or not np.isfinite(r.h1_atr) or r.h1_atr<=0:return False
    if side==1:
        return (r.close>r.sma480 and r.sma20>r.sma75>r.sma200 and r.sma200<r.sma480 and
                (r.sma480-r.sma200)>.25*r.h1_atr and
                (r.gap75_200-r.gap75_200_24)>=cfg.expansion_atr*r.h1_atr)
    return (r.close<r.sma480 and r.sma20<r.sma75<r.sma200 and r.sma200>r.sma480 and
            (r.sma200-r.sma480)>.25*r.h1_atr and
            ((-r.gap75_200)-(-r.gap75_200_24))>=cfg.expansion_atr*r.h1_atr)

def ma_abcd_reject(r,side):
    p=r.close; a,b,c,d=r.sma20,r.sma75,r.sma200,r.sma480
    if side==1:return ((p<c and p<d) or (a<c and a<d) or (p<c and a<c) or (p<d and a<d))
    return ((p>c and p>d) or (a>c and a>d) or (p>c and a>c) or (p>d and a>d))

def structural_level_reject(levels,t,entry,side,h4atr,cfg):
    if not np.isfinite(h4atr) or h4atr<=0:return False
    active=levels[(levels.active_time<=t)&(levels.expiry_time>t)]
    if side==1: q=active[active.price>entry]
    else: q=active[active.price<entry]
    if q.empty:return False
    dist=(q.price-entry).abs().min()
    return dist/h4atr<=cfg.h4_level_tol_atr

def inverse_trend_pass(h1p,h1,t,side,point):
    if point==1:return True
    ps=h1p[h1p.confirm_time<=t]
    hs=ps[ps.kind=='H'].tail(3); ls=ps[ps.kind=='L'].tail(3)
    if len(hs)<3 or len(ls)<3:return True
    hp=hs.price.to_numpy(); lp=ls.price.to_numpy()
    if side==1:
        inv=(hp[0]>hp[1]>hp[2] and lp[0]>lp[1]>lp[2])
        if not inv:return True
        # line through latest two pivot highs, evaluated at latest completed H1 index
        a,b=hs.iloc[-2],hs.iloc[-1]; cur=int(h1[h1.avail_time<=t].iloc[-1].h1i)
        if b.pivot_i==a.pivot_i:return True
        line=a.price+(b.price-a.price)*(cur-a.pivot_i)/(b.pivot_i-a.pivot_i)
        close=float(h1[h1.avail_time<=t].iloc[-1].close)
        return close>line
    inv=(hp[0]<hp[1]<hp[2] and lp[0]<lp[1]<lp[2])
    if not inv:return True
    a,b=ls.iloc[-2],ls.iloc[-1]; cur=int(h1[h1.avail_time<=t].iloc[-1].h1i)
    if b.pivot_i==a.pivot_i:return True
    line=a.price+(b.price-a.price)*(cur-a.pivot_i)/(b.pivot_i-a.pivot_i)
    close=float(h1[h1.avail_time<=t].iloc[-1].close)
    return close<line

def metrics(tr):
    if len(tr)==0:return dict(Trades=0,TotalR=0,AvgR=np.nan,PF=np.nan,MaxDD=np.nan,WinRate=np.nan)
    r=tr.R.to_numpy(float); gp=r[r>0].sum(); gl=-r[r<0].sum(); eq=np.cumsum(r); peak=np.maximum.accumulate(np.r_[0,eq]); dd=np.r_[0,eq]-peak
    return dict(Trades=len(r),TotalR=r.sum(),AvgR=r.mean(),PF=gp/gl if gl else np.inf,MaxDD=dd.min(),WinRate=(r>0).mean()*100)

def run_pair(pair,cfg=CFG):
    m,h1,h4,h1p,m15p=build_features(pair,cfg); levels=load_levels(pair) if cfg.use_h4_levels else None
    pip=.01 if pair.endswith('JPY') else .0001; minrisk=10*pip
    # pivot confirmations indexed by M15 bar time; effective next bar handled via confirm_time < current time
    piv_by_t={}
    for _,p in m15p.iterrows():piv_by_t.setdefault(p.confirm_time,[]).append(p)
    positions=[]; closed=[]
    states={1:0,-1:0}; pcount={1:0,-1:0}; regime_side=0; regime_id=0; regime_trades={1:[],2:[],3:[]}
    qhist={1:[],-1:[]}
    rsi_state={'buy_block':False,'sell_block':False,'peak':np.nan,'bottom':np.nan}; last_h4i=-1
    latest_pivot={'L':None,'H':None}
    prevK=prevD=np.nan

    for i,r in m.iterrows():
        t=r.time
        # update RSI state when a new completed H4 becomes available
        if cfg.use_h4_rsi and np.isfinite(r.h4i) and int(r.h4i)!=last_h4i:
            last_h4i=int(r.h4i); update_rsi_state(r.rsi,rsi_state)

        # 1) active SL hits for positions opened before this bar
        survivors=[]
        for p in positions:
            if p['entry_i']<i:
                hit=(r.low<=p['sl']) if p['side']==1 else (r.high>=p['sl'])
                if hit:
                    ex=p['sl']; R=(ex-p['entry'])*p['side']/p['risk']
                    if p.get('half_R') is not None: R=0.5*p['half_R']+0.5*R
                    p.update(exit=ex,ExitTime=t,R=R,exit_i=i);closed.append(p);continue
                # optional take-profit (checked after SL: same-bar SL wins)
                tp=p.get('tp')
                if tp is not None and p.get('half_R') is None and ((r.high>=tp) if p['side']==1 else (r.low<=tp)):
                    Rtp=(tp-p['entry'])*p['side']/p['risk']
                    if cfg.tp_half: p['half_R']=Rtp
                    else:
                        p.update(exit=tp,ExitTime=t,R=Rtp,exit_i=i,tp_hit=True);closed.append(p);continue
            survivors.append(p)
        positions=survivors

        # 2) +2R or delayed 240h activation; use latest already-confirmed pivot, effective this bar only if confirmed before t
        for p in positions:
            if not p['trail_on']:
                fav=(r.high-p['entry']) if p['side']==1 else (p['entry']-r.low)
                hit2=fav>=2*p['risk']
                delayed=cfg.use_delayed_zz and ((t-p['time']).total_seconds()/3600>=cfg.delayed_zz_hours)
                if hit2 or delayed:
                    p['trail_on']=True; p['trail_reason']='2R' if hit2 else '240h'
                    pv=latest_pivot['L' if p['side']==1 else 'H']
                    if pv is not None:
                        cand=pv['price']
                        if p['side']==1 and cand>p['sl']:p['sl']=cand
                        if p['side']==-1 and cand<p['sl']:p['sl']=cand

        # 3) pivot confirmed at this bar close; only affects next bar, so store after trailing activation
        for pv in piv_by_t.get(t,[]): latest_pivot[pv['kind']]=pv
        # update trailing from pivots confirmed PRIOR to current t only: newly stored pivot must wait, so skip here.
        # At next bar, latest pivot will be applied before SL check? Canonical rule says active SL hit first, then update,
        # hence apply after current SL check here for already-confirmed latest pivot.
        for p in positions:
            if p['trail_on']:
                pv=latest_pivot['L' if p['side']==1 else 'H']
                if pv is not None and pv['confirm_time']<t:
                    cand=pv['price']
                    if p['side']==1 and cand>p['sl']:p['sl']=cand
                    if p['side']==-1 and cand<p['sl']:p['sl']=cand

        # H1 regime reset
        rs=int(r.regside) if np.isfinite(r.regside) else 0
        if rs!=0 and rs!=regime_side:
            regime_side=rs;regime_id+=1;pcount={1:0,-1:0};regime_trades={1:[],2:[],3:[]};states={1:0,-1:0}

        # stochastic state transitions; one transition/bar/direction
        K,D=r.K,r.D
        completed=[]
        if np.isfinite(K) and np.isfinite(D):
            # BUY
            if states[1]==0 and K<20: states[1]=1
            elif states[1]==1 and np.isfinite(prevK) and np.isfinite(prevD) and prevK<=prevD and K>D: states[1]=2
            elif states[1]==2 and np.isfinite(prevK) and prevK<=20 and K>20: states[1]=0;completed.append(1)
            # SELL
            if states[-1]==0 and K>80: states[-1]=1
            elif states[-1]==1 and np.isfinite(prevK) and np.isfinite(prevD) and prevK>=prevD and K<D: states[-1]=2
            elif states[-1]==2 and np.isfinite(prevK) and prevK>=80 and K<80: states[-1]=0;completed.append(-1)
        prevK,prevD=K,D

        for side in completed:
            if side!=regime_side: continue
            # current P mode consumes immediately (before downstream rejects)
            if cfg.p_count_mode=='signal': pcount[side]+=1; point=pcount[side]
            else: point=None
            if point is not None and point>cfg.max_entry_point: continue
            # enough HTF data
            vals=[r.h1_atr,r.sma20,r.sma75,r.sma200,r.sma480,r.s200,r.s480]
            if not all(np.isfinite(x) for x in vals): continue
            # Trend: mandatory SMA200 slope + 200/480 relation (B may waive relation)
            if side==1 and r.s200<cfg.s200_min: continue
            if side==-1 and r.s200>-cfg.s200_min: continue
            rel=ma_relation_pass(r,side,cfg); exc=expansion_exception(r,side,cfg)
            if not (rel or exc): continue

            # q75 qualifying point: trend + stoch has now passed. Past only, then append current.
            strength=min(r.s200,r.s480) if side==1 else min(-r.s200,-r.s480)
            hist=qhist[side]; qrej=False
            if len(hist)>=cfg.q75_warmup:
                q=np.quantile(hist,.75); qrej=strength>q
            hist.append(float(strength))
            if qrej: continue

            # P-independent downstream filters
            if ma_abcd_reject(r,side): continue
            if cfg.use_h4_rsi and not h4_rsi_allowed(side,r.rsi,rsi_state): continue
            if cfg.use_h4_levels and structural_level_reject(levels,t,r.close,side,r.h4_atr,cfg): continue

            # eligible P alternative assigns P only after P-independent filters
            if cfg.p_count_mode=='eligible':
                pcount[side]+=1; point=pcount[side]
                if point>cfg.max_entry_point: continue

            if cfg.use_inverse_trend and not inverse_trend_pass(h1p,h1,t,side,point): continue

            # P3 conditions based on actually entered P1/P2 of current regime
            if point==3:
                p1s=regime_trades[1];p2s=regime_trades[2]
                if not p1s or not p2s: continue
                p1=p1s[-1];p2=p2s[-1]
                def curR(p):
                    if 'R' in p:return p['R']
                    return (r.close-p['entry'])*p['side']/p['risk']
                if curR(p1)<=0 and curR(p2)<=0: continue
                def mfe_atr(p):
                    seg=m.iloc[p['entry_i']:i+1]
                    mfe=(seg.high.max()-p['entry']) if p['side']==1 else (p['entry']-seg.low.min())
                    ea=p.get('entry_atr',np.nan)
                    return mfe/ea if np.isfinite(ea) and ea>0 else -np.inf
                if mfe_atr(p1)<cfg.p3_mfe_atr or mfe_atr(p2)<cfg.p3_mfe_atr: continue

            if cfg.extra_filter is not None and not cfg.extra_filter(t,side): continue
            if len(positions)>=cfg.max_positions: continue
            entry=float(r.close); base=float(r.sma200)+( -minrisk if side==1 else minrisk)
            if side==1: sl=min(base,entry-minrisk)
            else: sl=max(base,entry+minrisk)
            risk=abs(entry-sl)
            p={'pair':pair,'side':side,'point':point,'regime_id':regime_id,'entry_i':i,'time':t,'entry':entry,
               'initial_sl':sl,'sl':sl,'risk':risk,'trail_on':False,'trail_reason':'','entry_atr':float(r.atr),'B_exception':bool(exc and not rel)}
            if cfg.tp_fn is not None: p['tp']=cfg.tp_fn(t,side,entry,risk)
            positions.append(p);regime_trades[point].append(p)

    # mark open at end using last close
    last=m.iloc[-1]
    for p in positions:
        ex=float(last.close);R=(ex-p['entry'])*p['side']/p['risk']
        if p.get('half_R') is not None: R=0.5*p['half_R']+0.5*R
        p.update(exit=ex,ExitTime=last.time,R=R,exit_i=len(m)-1,open_end=True);closed.append(p)
    return pd.DataFrame(closed)

def run_all(cfg=CFG):
    alltr=[]
    for p in PAIRS:
        print('RUN',p,flush=True); x=run_pair(p,cfg); print(' ',len(x),metrics(x),flush=True);alltr.append(x)
    tr=pd.concat(alltr,ignore_index=True).sort_values(['time','pair']).reset_index(drop=True)
    return tr

if __name__=='__main__':
    tr=run_all(CFG)
    tr.to_csv(ROOT/'canonical_full_v1_trades.csv',index=False)
    sm=pd.DataFrame([{'scope':'ALL',**metrics(tr)}]+[{'scope':p,**metrics(g)} for p,g in tr.groupby('pair')])
    sm.to_csv(ROOT/'canonical_full_v1_summary.csv',index=False)
    print(sm.to_string(index=False))