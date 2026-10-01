"""Cross-account REAL trade analysis for Trade Tracker.

Usage:
  py trade_history_analysis.py
  py trade_history_analysis.py --years 5
  py trade_history_analysis.py --group-gap-hours 24 --min-samples 5

Reads:
- mt5_accounts.json: dedicated read-only account terminals
- GAS getEntries: app records (only status=決済; missed trades are ignored)
Writes local analysis JSON/CSV only. It never writes to GAS or MT5.
"""
import argparse,csv,json,math,os,pathlib,subprocess,sys
from collections import defaultdict
from datetime import datetime,timezone,timedelta
import requests

ROOT=pathlib.Path(__file__).parent
DEFAULT_GAS_URL="https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
GAS_URL=os.getenv("EA_GAS_URL",DEFAULT_GAS_URL)
ACCOUNTS=pathlib.Path(os.getenv("EA_MT5_ACCOUNTS_FILE",str(ROOT/"mt5_accounts.json")))
MAGIC=int(os.getenv("EA_MAGIC","560001"))

def dt(v):
    if not v:return None
    s=str(v).strip().replace("Z","+00:00")
    try:
        x=datetime.fromisoformat(s)
        return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
    except Exception:return None

def app_dt(date,time=""):
    s=str(date or "").split("T")[0].replace("/","-")
    if not s:return None
    try:
        # App date/time is Japan time by contract.
        return datetime.fromisoformat(s+"T"+(str(time or "00:00")[:5])+":00+09:00").astimezone(timezone.utc)
    except Exception:return None

def f(v):
    try:return float(v)
    except Exception:return 0.0

def worker(cfg,action,**kw):
    req={"config":cfg,"action":action,**kw}
    r=subprocess.run([sys.executable,str(ROOT/"mt5_history_worker.py"),json.dumps(req,ensure_ascii=False)],
                     capture_output=True,text=True,timeout=120)
    if r.returncode!=0:raise RuntimeError((r.stderr or r.stdout or "worker failed").strip())
    x=json.loads(r.stdout or "{}")
    if not x.get("ok"):raise RuntimeError(x.get("error","worker failed"))
    return x

def configs():
    raw=json.loads(ACCOUNTS.read_text(encoding="utf-8-sig"))
    return [x for x in raw.get("accounts",raw) if x.get("enabled",True)]

def fetch_app():
    r=requests.get(GAS_URL,params={"action":"getEntries"},timeout=30);r.raise_for_status()
    x=r.json();rows=x.get("data",x)
    # User requirement: actual trades only. 決済（見逃し） is intentionally excluded.
    return [e for e in rows if str(e.get("ステータス","")).strip()=="決済"]

def deal_direction(d):
    # MT5 DEAL_TYPE_BUY=0 / DEAL_TYPE_SELL=1 for trade deals.
    return "BUY" if int(d["type"])==0 else "SELL" if int(d["type"])==1 else ""

def positions_from_deals(deals):
    by=defaultdict(list)
    for d in deals: by[(d["account"],d["server"],d["position_id"])].append(d)
    out=[]
    for (account,server,pid),xs in by.items():
        xs.sort(key=lambda x:(x["time_msc"],x["ticket"]))
        entries=[x for x in xs if int(x["entry"]) in (0,2)] # IN / INOUT
        exits=[x for x in xs if int(x["entry"]) in (1,2,3)] # OUT / INOUT / OUT_BY
        if not entries or not exits:continue
        # Direction is based on entry side. Reversal positions are rare; keep first side.
        direction=deal_direction(entries[0])
        if not direction:continue
        ev=sum(x["volume"] for x in entries); xv=sum(x["volume"] for x in exits)
        ep=sum(x["price"]*x["volume"] for x in entries)/ev if ev else entries[0]["price"]
        xp=sum(x["price"]*x["volume"] for x in exits)/xv if xv else exits[-1]["price"]
        start=dt(entries[0]["time"]);end=max(dt(x["time"]) for x in exits)
        pnl=sum(x["profit"]+x["commission"]+x["swap"]+x["fee"] for x in xs)
        symbol=entries[0]["symbol"]
        out.append({"position_id":pid,"account":account,"server":server,"symbol":symbol,
          "broker_symbol":entries[0]["broker_symbol"],"direction":direction,"entry_time":start,
          "exit_time":end,"entry_price":ep,"exit_price":xp,"entry_volume":ev,"exit_volume":xv,
          "pnl":pnl,"entry_count":len(entries),"deal_count":len(xs),"magic":entries[0]["magic"]})
    return sorted(out,key=lambda x:x["entry_time"])

def group_positions(pos,gap_hours):
    """Merge split/continuous entries without pretending exact ticket=one trade.

    Same account+symbol+direction positions are merged when their active periods overlap,
    or the next entry starts within gap_hours after the prior group's last exit.
    """
    by=defaultdict(list)
    for p in pos:by[(p["account"],p["server"],p["symbol"],p["direction"])].append(p)
    groups=[]
    for key,xs in by.items():
        xs.sort(key=lambda x:x["entry_time"]);cur=None
        for p in xs:
            if cur is None or p["entry_time"]>cur["exit_time"]+timedelta(hours=gap_hours):
                if cur:groups.append(cur)
                cur=dict(p);cur["position_ids"]=[p["position_id"]];cur["position_count"]=1
            else:
                total=cur["entry_volume"]+p["entry_volume"]
                cur["entry_price"]=(cur["entry_price"]*cur["entry_volume"]+p["entry_price"]*p["entry_volume"])/total if total else cur["entry_price"]
                cur["entry_volume"]=total;cur["exit_volume"]+=p["exit_volume"];cur["pnl"]+=p["pnl"]
                cur["exit_time"]=max(cur["exit_time"],p["exit_time"]);cur["exit_price"]=p["exit_price"]
                cur["entry_count"]+=p["entry_count"];cur["deal_count"]+=p["deal_count"]
                cur["position_ids"].append(p["position_id"]);cur["position_count"]+=1
        if cur:groups.append(cur)
    groups.sort(key=lambda x:x["entry_time"])
    for i,g in enumerate(groups,1):
        g["trade_id"]=f"T{i:05d}"
        g["holding_hours"]=(g["exit_time"]-g["entry_time"]).total_seconds()/3600
        g["entry_hour_jst"]=g["entry_time"].astimezone(timezone(timedelta(hours=9))).hour
        g["weekday"]=g["entry_time"].astimezone(timezone(timedelta(hours=9))).strftime("%a")
        g["source"]="EA" if int(g["magic"])==MAGIC else "MANUAL"
    return groups

def norm_pair(e):
    s=str(e.get("PairName（元）") or e.get("PairName") or e.get("Pair") or "").upper().replace("#","")
    return "XAUUSD" if s=="GOLD" else s

def norm_dir(e):
    s=str(e.get("Direction") or e.get("方向") or "").upper()
    return "BUY" if "BUY" in s else "SELL" if "SELL" in s else ""

def match_app(groups,apps):
    """Loose date-based enrichment. MT5 remains authoritative for times/PnL."""
    used=set()
    for g in groups:
        best=None
        for i,a in enumerate(apps):
            if i in used or norm_pair(a)!=g["symbol"] or norm_dir(a)!=g["direction"]:continue
            at=app_dt(a.get("EntryDate"),a.get("EntryTime"))
            if not at:continue
            # App time may be approximate. Date proximity matters more than minute precision.
            days=abs((at.date()-g["entry_time"].date()).days)
            if days>4:continue
            score=100-days*20
            ae=app_dt(a.get("ExitDate"),a.get("ExitTime"))
            if ae:
                score-=min(20,abs((ae.date()-g["exit_time"].date()).days)*5)
            if best is None or score>best[0]:best=(score,i,a)
        if best:
            score,i,a=best;used.add(i);g["app_match_score"]=score;g["app_entry_id"]=a.get("EntryID","")
            # Preserve all app fields so Dow/TL/MA definitions can evolve without changing Python.
            g["app"]=a
        else:g["app_match_score"]=0;g["app_entry_id"]="";g["app"]={}
    return groups

def attach_features(groups,cfgs):
    fmap={(str(c["login"]),str(c["server"])):c for c in cfgs}
    by=defaultdict(list)
    for g in groups:by[(g["account"],g["server"])].append(g)
    for key,gs in by.items():
        cfg=fmap.get(key)
        if not cfg:continue
        payload=[{"trade_id":g["trade_id"],"symbol":g["symbol"],"broker_symbol":g["broker_symbol"],
                  "entry_time":g["entry_time"].isoformat()} for g in gs]
        try:
            ans=worker(cfg,"features",trades=payload)
            features={x["trade_id"]:x for x in ans["features"]}
            for g in gs:g.update(features.get(g["trade_id"],{}))
        except Exception as e:
            for g in gs:g["feature_error"]=str(e)
    return groups

def pip_size(symbol):
    return 0.01 if symbol.endswith("JPY") or symbol=="XAUUSD" else 0.0001

def classify_no_move(g,args):
    # Do not remove real quick losses. Exclude only quick trades whose absolute move AND P/L are tiny.
    move_pips=abs(g["exit_price"]-g["entry_price"])/pip_size(g["symbol"])
    g["move_pips_abs"]=move_pips
    g["analysis_excluded"]=bool(g["holding_hours"]<args.abort_hours and move_pips<args.abort_pips and abs(g["pnl"])<args.abort_money)
    g["exclude_reason"]="QUICK_NO_MOVE" if g["analysis_excluded"] else ""
    return g

def value(g,key):
    a=g.get("app") or {}
    if key=="entry_hour":return str(g["entry_hour_jst"])
    if key=="weekday":return g["weekday"]
    if key=="symbol":return g["symbol"]
    if key=="direction":return g["direction"]
    if key=="h1_ma20_75":return "20>75" if g.get("h1_ma20_gt_75") is True else "20<75" if g.get("h1_ma20_gt_75") is False else ""
    if key=="h1_ma200_480":return "200>480" if g.get("h1_ma200_gt_480") is True else "200<480" if g.get("h1_ma200_gt_480") is False else ""
    aliases={
      "dow":["DowRule","ダウ認識"],"session":["時間帯"],"tl_push":["TL推進","TL推進認識"],
      "tl_reverse":["TL逆トレ","TL逆トレ認識"],"h1ma_app":["H1MA20.80_J","H1MA20.80"],
      "h4ma_app":["H4MA20.80_J","H4MA20.80"],"h4":["H4"],"h1":["H1"],
      "entry_review":["エントリー振り返り"]
    }
    for k in aliases.get(key,[]):
        if str(a.get(k,"")).strip():return str(a[k]).strip()
    return ""

def stats(rows):
    n=len(rows);wins=sum(1 for x in rows if x["pnl"]>0);loss=sum(1 for x in rows if x["pnl"]<0)
    gp=sum(x["pnl"] for x in rows if x["pnl"]>0);gl=-sum(x["pnl"] for x in rows if x["pnl"]<0)
    return {"n":n,"wins":wins,"losses":loss,"win_rate":round(100*wins/n,1) if n else 0,
      "total_pnl":round(sum(x["pnl"] for x in rows),2),"avg_pnl":round(sum(x["pnl"] for x in rows)/n,2) if n else 0,
      "profit_factor":round(gp/gl,3) if gl else None}

def analyze(groups,min_samples):
    rows=[g for g in groups if not g["analysis_excluded"]]
    factors=["symbol","direction","weekday","entry_hour","session","dow","tl_push","tl_reverse",
             "h1ma_app","h4ma_app","h4","h1","entry_review","h1_ma20_75","h1_ma200_480"]
    result={"overall":stats(rows),"excluded":len(groups)-len(rows),"factors":{}}
    for fac in factors:
        buckets=defaultdict(list)
        for g in rows:
            v=value(g,fac)
            if v:buckets[v].append(g)
        result["factors"][fac]=[{"value":v,**stats(xs)} for v,xs in buckets.items() if len(xs)>=min_samples]
    return result

def flat(g):
    a=g.get("app") or {}
    keys=["DowRule","ダウ認識","時間帯","TL推進","TL推進認識","TL逆トレ","TL逆トレ認識","H1MA20.80_J","H4MA20.80_J","H4","H1","エントリー振り返り"]
    out={k:v for k,v in g.items() if k!="app"}
    for k in keys:out["app_"+k]=a.get(k,"")
    for k in ("entry_time","exit_time"):out[k]=g[k].isoformat()
    out["position_ids"]="|".join(g["position_ids"])
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--years",type=float,default=10)
    ap.add_argument("--group-gap-hours",type=float,default=24)
    ap.add_argument("--abort-hours",type=float,default=0.25,help="quick-no-move time threshold")
    ap.add_argument("--abort-pips",type=float,default=3.0)
    ap.add_argument("--abort-money",type=float,default=1000.0)
    ap.add_argument("--min-samples",type=int,default=5)
    ap.add_argument("--no-features",action="store_true")
    args=ap.parse_args()
    end=datetime.now(timezone.utc);start=end-timedelta(days=int(args.years*365.25))
    cfgs=configs();all_deals=[];errors=[]
    print(f"Accounts: {len(cfgs)} / period: {start.date()} - {end.date()}")
    for c in cfgs:
        try:
            x=worker(c,"history",start=start.isoformat(),end=end.isoformat())
            all_deals.extend(x["deals"]);print(f"[OK] {c['login']} deals={len(x['deals'])}")
        except Exception as e:errors.append({"account":str(c.get("login")),"error":str(e)});print(f"[FAIL] {c.get('login')}: {e}")
    pos=positions_from_deals(all_deals);groups=group_positions(pos,args.group_gap_hours)
    apps=fetch_app();groups=match_app(groups,apps)
    if not args.no_features:groups=attach_features(groups,cfgs)
    groups=[classify_no_move(g,args) for g in groups]
    report=analyze(groups,args.min_samples)
    report["meta"]={"generated_at":datetime.now(timezone.utc).isoformat(),"accounts_configured":len(cfgs),
      "account_errors":errors,"positions":len(pos),"trade_groups":len(groups),"app_real_trades":len(apps),
      "app_matched":sum(1 for g in groups if g["app_entry_id"]),"group_gap_hours":args.group_gap_hours,
      "quick_no_move_rule":{"hours_lt":args.abort_hours,"move_pips_lt":args.abort_pips,"abs_pnl_lt":args.abort_money}}
    outdir=ROOT/"analysis_output";outdir.mkdir(exist_ok=True)
    (outdir/"trade_analysis.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    rows=[flat(g) for g in groups]
    if rows:
        fields=sorted(set().union(*(r.keys() for r in rows)))
        with open(outdir/"master_trades.csv","w",newline="",encoding="utf-8-sig") as fh:
            w=csv.DictWriter(fh,fieldnames=fields);w.writeheader();w.writerows(rows)
    print("\n=== SUMMARY ===")
    print(json.dumps({"meta":report["meta"],"overall":report["overall"]},ensure_ascii=False,indent=2))
    print(f"\nSaved: {outdir/'trade_analysis.json'}")
    print(f"Saved: {outdir/'master_trades.csv'}")

if __name__=="__main__":main()
